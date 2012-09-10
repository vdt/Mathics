# -*- coding: utf8 -*-

"""
File Operations
"""

import io
from os.path import getatime, getmtime, getctime

from mathics.core.expression import Expression, String, Symbol, from_python
from mathics.builtin.base import Builtin, Predefined

STREAMS = {}

class ImportFormats(Predefined):
    """
    <dl>
    <dt>'$ImportFormats'
        <dd>returns a list of file formats supported by Import.
    </dl>
    
    >> $ImportFormats
     = {}
    """

    name = '$ImportFormats'

    def evaluate(self, evaluation):
        return Expression('List')

class ExportFormats(Predefined):
    """
    <dl>
    <dt>'$ExportFormats'
        <dd>returns a list of file formats supported by Export.
    </dl>
    
    >> $ExportFormats
     = {}
    """

    name = '$ExportFormats'

    def evaluate(self, evaluation):
        return Expression('List')

class Read(Builtin):
    """
    <dl>
    <dt>'Read[stream]'
        <dd>reads the input stream and returns one expression.
    <dt>'Read[stream, type]
        <dd>reads the input stream and returns object of the given type.
    </dl>

    ## Malformed InputString
    #> Read[InputStream[String], {Word, Number}]
     : InputStream[String] is not string, InputStream[], or OutputStream[]
     = Read[InputStream[String], {Word, Number}]

    ## Correctly formed InputString but not open
    #> Read[InputStream[String, -1], {Word, Number}]
     : InputSteam[String, -1] is not open
     = Read[InputStream[String, -1], {Word, Number}]

    #> str = StringToStream["abc123"];
    #> Read[str, String]
     = abc123
    #> Read[str, String]
     = EndOfFile
    
    #> str = StringToStream["abc 123"];
    #> Read[str, Word]
     = abc
    #> Read[str, Word]
     = 123
    #> Read[str, Word]
     = EndOfFile
    #> str = StringToStream[""];
    #> Read[str, Word]
     = EndOfFile
    #> Read[str, Word]
     = EndOfFile
    """

    messages = {
        'readf': '`1` is not a valif format specificiation',
        'openx': '`1` is not open',
    }

    rules = {
        'Read[stream_]': 'Read[stream, Expression]',
    }

    def apply(self, name, n, types, evaluation):
        'Read[InputStream[name_, n_], types_]'
        global STREAMS
    
        stream = STREAMS.get(n.to_python())

        if stream is None:
            evaluation.message('Read', 'openx', Expression('InputSteam', name, n))
            return
        
        types = types.to_python()
        if not isinstance(types, list):
            types = [types]
    
        READ_TYPES = ['Byte', 'Character', 'Expression', 'Number', 'Real', 'Record', 'String', 'Word']

        if not all(isinstance(typ, basestring) and typ in READ_TYPES for typ in types):
            evaluation.message('Read', 'readf', from_python(typ))
            return
        
        name = name.to_python()

        result = []

        #TODO: Implement these as options
        word_separators = [' ', '\t']
        record_separators = ['\n', '\r\n', '\r']

        def word_reader(stream, word_separators):
            word_separators = [' ', '\t', '\n']
            while True:
                word = ''
                while True:
                    tmp = stream.read(1)

                    if tmp == '':
                        if word == '':
                            raise EOFError
                        yield word

                    if tmp in word_separators:
                        if word == '':
                            break
                        else:
                            yield word
                    else:
                        word += tmp

        read_word = word_reader(stream, word_separators)
        for typ in types:
            try:
                if typ == 'Byte':
                    tmp = stream.read(1)
                    if len(tmp) == 0:
                        raise EOFError
                    result.append(ord(tmp))
                elif typ == 'Character':
                    result.append(stream.read(1))
                elif typ == 'Expression':
                    pass #TODO
                elif typ == 'Number':
                    pass #TODO
                elif typ == 'Real':
                    pass #TODO
                elif typ == 'Record':
                    pass #TODO
                elif typ == 'String':
                    tmp = stream.readline()
                    if len(tmp) == 0:
                        raise EOFError
                    result.append(tmp)
                elif typ == 'Word':
                    tmp = read_word.next()
                    result.append(tmp)
                        
            except EOFError:
                return from_python('EndOfFile')

        if len(result) == 1:
            return from_python(*result)

        return from_python(result)

    def apply_nostream(self, arg1, arg2, evaluation):
        'Read[arg1_, arg2_]'
        evaluation.message('General', 'stream', arg1)
        return
                
class Write(Builtin):
    """
    <dl>
    <dt>'Write[channel, expr]'
        <dd>writes the expression to the output channel as a string."
    </dl>
    """

    def apply(self, name, n, expr, evaluation):
        'WriteString[OutputStream[name_, n_], expr___]'
        global STREAMS
        stream = STREAMS[n.to_python()]

        expr = expr.get_sequence()
        expr = Expression('Row', Expression('List', *expr))

        evaluation.format = 'text'
        text = evaluation.format_output(from_python(expr))
        stream.write(text)
        return Symbol('Null')

class WriteString(Builtin):
    """
    <dl>
    <dt>'Write[stream, expr1, expr2, ... ]'
        <dd>writes the expressions to the output channel followed by a newline"
    </dl>
    """

    messages = {
        'strml': '`1` is not a string, stream, or list of strings and streams.',
    }

    def apply(self, name, n, expr, evaluation):
        'WriteString[OutputStream[name_, n_], expr___]'
        global STREAMS
        stream = STREAMS[n.to_python()]

        exprs = expr.get_sequence()
        for e in exprs:
            if not isinstance(e, String):
                evaluation.message('WriteString', 'strml', e) # Mathematica gets this message wrong
                return

        text = map(lambda x: x.to_python().strip('"'), exprs)
        text = ''.join(text)
        stream.write(text)
        return Symbol('Null')

class Save(Builtin):
    pass

class _OpenAction(Builtin):
    def apply(self, path, evaluation):
        '%(name)s[path_]'

        path_string = path.to_python().strip('"')

        try:
            stream = io.open(path_string, mode=self.mode)
        except IOError:
            evaluation.message('General', 'noopen', path)
            return

        n = _put_stream(stream)
        result = Expression(self.stream_type, path, n)
        global _STREAMS
        _STREAMS[n] = result

        return result

class OpenRead(_OpenAction):
    """
    <dl>
    <dt>'OpenRead["file"]'
        <dd>opens a file and returns an InputStream. 
    </dl>
    """
    mode = 'r'
    stream_type = 'InputStream'

class OpenWrite(_OpenAction):
    """
    <dl>
    <dt>'OpenWrite["file"]'
        <dd>opens a file and returns an OutputStream. 
    </dl>
    """
    
    mode = 'w'
    stream_type = 'OutputStream'


class OpenAppend(_OpenAction):
    """
    <dl>
    <dt>'OpenAppend["file"]'
        <dd>opens a file and returns an OutputStream to which writes are appended. 
    </dl>
    """

    mode = 'a'
    stream_type = 'OutputStream'

class Import(Builtin):
    pass

class Export(Builtin):
    pass

class ReadList(Builtin):
    """
    <dl>
    <dt>'ReadList["file"]
        <dd>Reads all the expressions until the end of file.
    </dl>
    """

    rules = {
        'ReadList[stream_]': 'ReadList[stream, Expression]',
    }

    def apply(self, name, n, types, evaluation):
        'ReadList[InputStream[name_, n_], types_]'
        global STREAMS

        stream = STREAMS[n.to_python()]

        types = types.to_python()
        if not isinstance(types, list):
            types = [types]

        name = name.to_python()

        result = []

        for typ in types:
            if typ == 'String':
                result.append(stream.readlines())
            else:
                #TODO
                pass

        if len(result) == 1:
            return from_python(*result)

        return from_python(result)

class FilePrint(Builtin):
    """
    <dl>
    <dt>'FilePrint["file"]
        <dd>prints the raw contents of $file$.
    </dl>
    """

    def apply(self, path, evaluation):
        'FilePrint[path_]'
        path = path.to_python().strip('"')

        try:
            f = open(path, 'r')
            result = f.read()
            f.close()
        except IOError:
            evaluation.message('General', 'noopen', path)
            return

        return from_python(result)

class Close(Builtin):
    """
    <dl>
    <dt>'Close[stream]'
        <dd>closes an input or output stream.
    </dl>
    
    """
     
    def apply_input(self, name, n, evaluation):
        'Close[InputStream[name_, n_]]'
        global STREAMS
        stream = STREAMS[n.to_python()]

        if stream.closed:
            evaluation.message('General', 'openx', name)
            return

        stream.close()
        return Symbol('Null')

    def apply_output(self, name, n, evaluation):
        'Close[OutputStream[name_, n_]]'
        global STREAMS
        stream = STREAMS[n.to_python()]

        if stream.closed:
            evaluation.message('General', 'openx', name)
            return

        stream.close()
        return Symbol('Null')

    def apply_default(self, stream, evaluation):
        'Close[stream_]'
        evaluation.message('General', 'stream', stream)
        return

class InputStream(Builtin):
    """
    <dl>
    <dt>'InputStream["name", n]'
        <dd>represents an input stream.
    </dl>
    """

    def apply(self, name, n, evaluation):
        'InputStream[name_, n_]'
        return

class OutputStream(Builtin):
    """
    <dl>
    <dt>'OutputStream["name", n]'
        <dd>represents an output stream.
    </dl>
    """
    def apply(self, name, n, evaluation):
        'OutputStream[name_, n_]'
        return


class StringToStream(Builtin):
    """
    <dl>
    <dt>'StringToStream["string"]'
        <dd>converts a string to an open stream.
    </dl>

    >> StringToStream["abc 123"]
     = InputStream[String, 1]
    """
    
    def apply(self, string, evaluation):
        'StringToStream[string_]'
        pystring = string.to_python().strip('"')
        stream = io.StringIO(initial_value=unicode(pystring))
        n = _put_stream(stream)
        result = Expression('InputStream', from_python('String'), n)

        global _STREAMS
        _STREAMS[n] = result

        return result

class Streams(Builtin):
    """
    <dl>
    <dt>'Streams[]'
        <dd>returns a list of all open streams.
    </dl>
    """

    def apply(self, evaluation):
        'Streams[]'
        global _STREAMS
        return Expression('List', *_STREAMS.values())

def _put_stream(stream):
    global STREAMS
    global _STREAMS
    global NSTREAMS

    try:
        _STREAMS
    except NameError:
        STREAMS = {}    # Python repr
        _STREAMS = {}   # Mathics repr
        NSTREAMS = 0    # Max stream number

    NSTREAMS += 1
    STREAMS[NSTREAMS] = stream
    return NSTREAMS

def _get_stream(n):
    global STREAMS
    return STREAMS[n]

class FileDate(Builtin):
    """
    <dl>
    <dt>'FileDate["file", "types"]'
        <dd>returns the time and date at which the file was last modified.
    </dl>
    """

    rules = {
        'FileDate[path_]': 'FileDate[path, "Modification"]',
    }

    def apply(self, path, timetype, evaluation):
        'FileDate[path_, timetype_]'
        path = path.to_python().strip('"')
        time_type = timetype.to_python().strip('"')
        if time_type == 'Access':
            time = getatime(path)
        elif time_type in ['Creation', 'Change']:   # TODO: Fixing this cross platform is difficult
            time = getctime(path)
        elif time_type == 'Modification':
            time = getmtime(path)
        else:
            return

        # Mathematica measures epoch from Jan 1 1900, while python is from Jan 1 1970!
        return Expression('DateString', from_python(time + 2208988800))


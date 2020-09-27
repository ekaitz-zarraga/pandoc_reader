import subprocess
from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from datetime import datetime

class PandocReader(BaseReader):
    enabled = True
    file_extensions = ['md', 'markdown', 'mkd', 'mdown']

    def read(self, filename):
        with pelican_open(filename) as fp:
            text = tuple(fp.splitlines())

        metadata = {}
        init = text.index("...")
        end  = text[init:].index("---") + init

        metatext = "\n".join(text[init+1:end])
        metadata = load(metatext, Loader=Loader)

        if "Date" in metadata:
            # Back to string because PyYaml is way too clever
            metadata["Date"] = metadata["Date"].isoformat()

        finalmeta = {}
        for k,v in metadata.items():
            finalmeta[k.lower()] = self.process_metadata(k.lower(),v)

        content = "\n".join(text[:init] + text[end+1:])

        extra_args = self.settings.get('PANDOC_ARGS', [])
        extensions = self.settings.get('PANDOC_EXTENSIONS', '')
        if isinstance(extensions, list):
            extensions = ''.join(extensions)

        pandoc_cmd = ["pandoc", "--from=markdown" + extensions, "--to=html5"]
        pandoc_cmd.extend(extra_args)

        proc = subprocess.Popen(pandoc_cmd,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE)

        output = proc.communicate(content.encode('utf-8'))[0].decode('utf-8')
        status = proc.wait()
        if status:
            raise subprocess.CalledProcessError(status, pandoc_cmd)

        # Need that to make {static} -like tags be available
        output = output.replace("%7B", "{")
        output = output.replace("%7D", "}")

        return output, finalmeta

def add_reader(readers):
    for ext in PandocReader.file_extensions:
        readers.reader_classes[ext] = PandocReader

def register():
    signals.readers_init.connect(add_reader)

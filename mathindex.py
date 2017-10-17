"""Index math expressions from notebooks.
"""
import logging
import nbformat
import os
import sys

from nbconvert.filters.markdown_mistune import MarkdownWithMath, IPythonRenderer

log = logging.getLogger(__name__)

class MathRecordingRenderer(IPythonRenderer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.extracted_math = []

    def block_math(self, text):
        self.extracted_math.append('$$%s$$' % text)
        return super().block_math(text)

    def latex_environment(self, name, text):
        self.extracted_math.append('\\begin{%s}%s\\end{%s}' % (name, text, name))
        return super().latex_environment(name, text)

    def inline_math(self, text):
        self.extracted_math.append('$%s$' % text)
        return super().inline_math(text)

def scan_markdown(source):
    renderer = MathRecordingRenderer()
    MarkdownWithMath(renderer=renderer).render(source)
    return renderer.extracted_math

def scan_ipynb(file):
    nb = nbformat.read(file, as_version=4)
    math_idx = 0

    for cell_ix, cell in enumerate(nb.cells, start=1):
        if cell.cell_type == 'code':
            for output_ix, output in enumerate(cell.outputs, start=1):
                if output.output_type in ('display_data', 'execute_result') \
                        and 'text/latex' in output.data:
                    math_idx += 1
                    yield {
                        'cell': cell_ix,
                        'output_ix': output_ix,
                        'latex': output.data['text/latex'],
                        'url_fragment': 'MathJax-Element-%d-Frame' % math_idx,
                    }
        elif cell.cell_type == 'markdown':
            for latex in scan_markdown(cell.source):
                math_idx += 1
                yield {
                    'cell': cell_ix,
                    'latex': latex,
                    'url_fragment': 'MathJax-Element-%d-Frame' % math_idx,
                }

def filter_subdirs(dirnames):
    # Python makes a 'build' directory with a copy of all files to be packaged.
    # Ignore these.
    dirnames[:] = [d for d in dirnames if d != 'build']

def scan_directory(directory):
    """Walk files in a directory, yielding (filename, info) pairs of indexable
    objects.

    :param str directory: Path to a directory to search

    Only files with a ``.py`` or ``.pyw`` extension will be scanned.
    """
    for dirpath, dirnames, filenames in os.walk(directory):
        filter_subdirs(dirnames)

        for filename in filenames:
            if filename.endswith('.ipynb'):
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, directory)
                for match in scan_ipynb(filepath):
                    yield relpath, match

def _printline(info):
    print("#{url_fragment}: '{latex}'".format_map(info))

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', default='.',
                    help="file or directory to index")
    ap.add_argument('--gh-repo',
                    help="Github repo ID (e.g. ipython/ipython)")
    #ap.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if os.path.isdir(args.path):
        # Search directory
        current_filepath = None
        for filepath, info in scan_directory(args.path):
            if filepath != current_filepath:
                if current_filepath is not None:
                    print()  # Blank line between files
                current_filepath = filepath
                if args.gh_repo:
                    print('http://nbviewer.jupyter.org/github/{}/blob/master/{}'
                            .format(args.gh_repo, filepath))
                else:
                    print(filepath)
            _printline(info)

    elif os.path.exists(args.path):
        # Search file
        for info in scan_ipynb(args.path):
            _printline(info)

    else:
        sys.exit("No such file or directory: {}".format(args.path))

if __name__ == '__main__':
    main()

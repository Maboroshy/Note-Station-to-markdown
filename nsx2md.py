#!/usr/bin/env python

import os
import re
import sys
import time
import json
import shutil
import zipfile
import tempfile
import subprocess
import collections
import distutils.version

from pathlib import Path


# You can adjust some setting here. Default is for QOwnNotes app.
link_prepend = 'file:/'
absolute_links = False  # False for relative links
convert_spaces_in_links = False  # Replace spaces in links with '%20'
media_dir_name = 'media'
md_file_ext = 'md'
insert_title = True
insert_ctime = False
insert_mtime = False
creation_date_in_filename = False
force_windows_filename_limitations = False

############################################################################

Notebook = collections.namedtuple('Notebook', ['path', 'media_path'])


def sanitise_path_string(path_str):
    for char in (':', '/', '\\', '|'):
        path_str = path_str.replace(char, '-')
    for char in ('?', '*'):
        path_str = path_str.replace(char, '')
        path_str = path_str.replace('<', '(')
        path_str = path_str.replace('>', ')')
        path_str = path_str.replace('"', "'")

    return path_str


work_path = Path(__file__).parent
media_dir_name = sanitise_path_string(media_dir_name)
pandoc_input_file = tempfile.NamedTemporaryFile(delete=False)
pandoc_output_file = tempfile.NamedTemporaryFile(delete=False)


if not shutil.which('pandoc') and not os.path.isfile('pandoc'):
    print('Can\'t find pandoc. Please install pandoc or place it to the directory, where the script is.')
    exit()

try:
    pandoc_ver = subprocess.check_output(['pandoc', '-v'], timeout=3).decode('utf-8')[7:].split('\n', 1)[0]
    print('Found pandoc ' + pandoc_ver)
except Exception:
    pandoc_ver = '1.19.2.1'

if distutils.version.LooseVersion(pandoc_ver) < distutils.version.LooseVersion('1.16'):
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'markdown_strict+pipe_tables-raw_html',
                   '--no-wrap', '-o', pandoc_output_file.name, pandoc_input_file.name]
elif distutils.version.LooseVersion(pandoc_ver) < distutils.version.LooseVersion('1.19'):
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'markdown_strict+pipe_tables-raw_html',
                   '--wrap=none', '-o', pandoc_output_file.name, pandoc_input_file.name]
else:
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'markdown_strict+pipe_tables-raw_html',
                   '--wrap=none', '--atx-headers', '-o',
                   pandoc_output_file.name, pandoc_input_file.name]


if len(sys.argv) > 1:
    files_to_convert = [Path(path) for path in sys.argv[1:]]
else:
    files_to_convert = Path(work_path).glob('*.nsx')

if not files_to_convert:
    print('No .nsx files found')
    exit(1)


for file in files_to_convert:
    nsx_file = zipfile.ZipFile(str(file))
    config_data = json.loads(nsx_file.read('config.json').decode('utf-8'))

    notebook_id_to_path_index = {}

    for notebook_id in config_data['notebook']:
        notebook_data = json.loads(nsx_file.read(notebook_id).decode('utf-8'))
        notebook_title = notebook_data['title'] or 'Untitled'
        notebook_path = work_path / Path(sanitise_path_string(notebook_title))

        n = 1
        while notebook_path.is_dir():
            notebook_path = work_path / Path('{}_{}'.format(sanitise_path_string(notebook_title), n))
            n += 1

        notebook_media_path = Path(notebook_path / media_dir_name)
        notebook_media_path.mkdir(parents=True)

        notebook_id_to_path_index[notebook_id] = Notebook(notebook_path, notebook_media_path)


    converted_note_count = 0

    for note_id in config_data['note']:
        note_data = json.loads(nsx_file.read(note_id).decode('utf-8'))
        note_title = note_data.get('title', 'Untitled')
        note_ctime = note_data.get('ctime', '')
        note_mtime = note_data.get('mtime', '')
        parent_notebook_id = note_data['parent_id']
        parent_notebook = notebook_id_to_path_index[parent_notebook_id]

        print('Converting note "{}"'.format(note_title))

        content = re.sub('<img class="[^"]*syno-notestation-image-object" src=[^>]*ref="',
                         '<img src="', note_data.get('content', ''))


        Path(pandoc_input_file.name).write_text(content, 'utf-8')
        pandoc = subprocess.Popen(pandoc_args)
        pandoc.wait(5)
        content = Path(pandoc_output_file.name).read_text('utf-8')


        attachment_list = []

        for attachment_id in note_data.get('attachment', ''):

            ref = note_data['attachment'][attachment_id].get('ref', '')
            md5 = note_data['attachment'][attachment_id]['md5']
            source = note_data['attachment'][attachment_id].get('source', '')
            name = sanitise_path_string(note_data['attachment'][attachment_id]['name'])

            n = 1
            while Path(parent_notebook.media_path / name).is_file():
                name_parts = name.rpartition('.')
                name = ''.join((name_parts[0], '_{}'.format(n), name_parts[1], name_parts[2]))
                n += 1

            if absolute_links:
                link_path = ''.join((link_prepend, str(parent_notebook.media_path), '/', name))
            else:
                link_path = '/'.join((link_prepend, media_dir_name, name))

            if convert_spaces_in_links:
                link_path = link_path.replace(' ', '%20')

            try:
                Path(parent_notebook.media_path / name).write_bytes(nsx_file.read('file_' + md5))
                attachment_list.append('[{}]({})'.format(name, link_path))
            except Exception:
                if source:
                    attachment_list.append('[{}]({})'.format(name, source))
                else:
                    print('  Can\'t find attachment "{}" of note "{}"'.format(name, note_title))
                    attachment_list.append('[NOT FOUND]({})'.format(link_path))

            if ref and source:
                content = content.replace(ref, source)
            elif ref:
                content = content.replace(ref, link_path)


        if note_data.get('tag', '') or attachment_list or insert_title \
                or insert_ctime or insert_mtime:
            content = '\n' + content

        if insert_mtime and note_mtime:
            text_mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_mtime))
            content = 'Modified: {}  \n{}'.format(text_mtime, content)
        if insert_ctime and note_ctime:
            text_ctime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_ctime))
            content = 'Created: {}  \n{}'.format(text_ctime, content)
        if attachment_list:
            content = 'Attachments: {}  \n{}'.format(', '.join(attachment_list), content)
        if note_data.get('tag', ''):
            content = 'Tags: {}  \n{}'.format(', '.join(note_data['tag']), content)
        if insert_title:
            content = '{}\n{}\n{}'.format(note_title, '=' * len(note_title), content)

        if creation_date_in_filename and note_ctime:
            note_title = time.strftime('%Y-%m-%d ', time.localtime(note_ctime)) + note_title

        md_file_name = sanitise_path_string(note_title) or 'Untitled'
        md_file_path = Path(parent_notebook.path / '{}.{}'.format(md_file_name, md_file_ext))

        n = 1
        while md_file_path.is_file():
            md_file_path = Path(parent_notebook.path / ('{}_{}.{}'.format(
                                            sanitise_path_string(note_title), n, md_file_ext)))
            n += 1

        md_file_path.write_text(content, 'utf-8')
        converted_note_count += 1

    for notebook in notebook_id_to_path_index.values():
        try:
            notebook.media_path.rmdir()
        except OSError:
            pass


pandoc_input_file.close()
pandoc_output_file.close()
os.unlink(pandoc_input_file.name)
os.unlink(pandoc_output_file.name)

input('Converted {} notebooks and {} out of {} notes. Press Enter to quit...'.format(
            len(config_data['notebook']), converted_note_count, len(config_data['note'])))

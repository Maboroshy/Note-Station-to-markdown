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


work_path = Path(__file__).parent
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
    files = [Path(path) for path in sys.argv[1:]]
else:
    files = Path(work_path).glob('*.nsx')


for file in files:
    nsx = zipfile.ZipFile(str(file))
    config_data = json.loads(nsx.read('config.json').decode('utf-8'))

    for notebook in config_data['notebook']:
        notebook_data = json.loads(nsx.read(notebook).decode('utf-8'))
        notebook_title = notebook_data['title'] or 'Untitled'
        notebook_path = file.parent / Path(notebook_title)

        print('Converting notebook "{}"'.format(notebook_title))

        n = 1
        while notebook_path.is_dir():
            notebook_path = file.parent / Path('{}_{}'.format(notebook_title, n))
            n += 1

        notebook_media_path = Path(notebook_path / media_dir_name)
        notebook_media_path.mkdir(parents=True)

        for note in config_data['note']:
            note_data = json.loads(nsx.read(note).decode('utf-8'))
            note_title = note_data['title']
            note_ctime = note_data.get('ctime', '')
            note_mtime = note_data.get('mtime', '')

            if note_data['parent_id'] != notebook:
                continue


            content = re.sub('<img class="[^"]*syno-notestation-image-object" src=[^>]*ref="',
                             '<img src="', note_data.get('content', ''))


            Path(pandoc_input_file.name).write_text(content, 'utf-8')
            pandoc = subprocess.Popen(pandoc_args)
            pandoc.wait(5)
            content = Path(pandoc_output_file.name).read_text('utf-8')


            attachment_list = []

            for attachment in note_data.get('attachment', ''):

                ref = note_data['attachment'][attachment].get('ref', '')
                md5 = note_data['attachment'][attachment]['md5']
                name = note_data['attachment'][attachment]['name']
                source = note_data['attachment'][attachment].get('source', '')

                n = 1
                while Path(notebook_media_path / name).is_file():
                    name_parts = name.rpartition('.')
                    name = ''.join((name_parts[0], '_{}'.format(n), name_parts[1], name_parts[2]))
                    n += 1

                if Path(notebook_media_path / name).is_file():
                    name = str(round(time.time())) + '-' + name

                if absolute_links:
                    link_path = link_prepend + str(notebook_media_path) + '/' + name
                else:
                    link_path = link_prepend + '/' + media_dir_name + '/' + name

                if convert_spaces_in_links:
                    link_path = link_path.replace(' ', '%20')

                try:
                    Path(notebook_media_path / name).write_bytes(nsx.read('file_' + md5))
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


            md_file_name = note_title
            for char in (':', '/', '\\', '|'):
                md_file_name = md_file_name.replace(char, '-')
            for char in ('?', '*'):
                md_file_name = md_file_name.replace(char, '')
            md_file_name = md_file_name.replace('<', '(')
            md_file_name = md_file_name.replace('>', ')')
            md_file_name = md_file_name.replace('"', "'")

            md_file_path = Path(notebook_path / '{}.{}'.format(md_file_name, md_file_ext))

            n = 1
            while md_file_path.is_file():
                md_file_path = Path(notebook_path / ('{}_{}.{}'.format(md_file_name, n, md_file_ext)))
                n += 1

            md_file_path.write_text(content, 'utf-8')

        try:
            notebook_media_path.rmdir()
        except OSError:
            pass

pandoc_input_file.close()
pandoc_output_file.close()
os.unlink(pandoc_input_file.name)
os.unlink(pandoc_output_file.name)

input('Conversion finished. Press Enter to quit...')

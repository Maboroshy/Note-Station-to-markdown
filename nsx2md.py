#!/usr/bin/env python

import os
import re
import sys
import time
import json
import shutil
import zipfile
import tempfile
import platform
import subprocess
import distutils.version


# You can adjust some setting here. Default is for QOwnNotes app.
link_prepend = 'file://'
media_dir = 'media'
md_file_ext = 'md'
insert_title = True
insert_ctime = False
insert_mtime = False
creation_date_in_filename = False
force_windows_filename_limitations = False


if not shutil.which('pandoc') and not os.path.isfile('pandoc'):
    print('Can\'t find pandoc. Please install pandoc or place it to the directory, where the script is.')
    exit()

input_file = tempfile.NamedTemporaryFile(delete=False)
output_file = tempfile.NamedTemporaryFile(delete=False)

try:
    pandoc_ver = subprocess.check_output(['pandoc', '-v'], timeout=3).decode('utf-8')[7:].split('\n', 1)[0]
    print('Found pandoc ' + pandoc_ver)
except Exception:
    pandoc_ver = '1.19.2.1'

if distutils.version.LooseVersion(pandoc_ver) < distutils.version.LooseVersion('1.16'):
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'markdown_strict+pipe_tables-raw_html', '--no-wrap',
                   '-o', output_file.name, input_file.name]
elif distutils.version.LooseVersion(pandoc_ver) < distutils.version.LooseVersion('1.19'):
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'markdown_strict+pipe_tables-raw_html', '--wrap=none',
                   '-o', output_file.name, input_file.name]
else:
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'markdown_strict+pipe_tables-raw_html', '--wrap=none', '--atx-headers',
                   '-o', output_file.name, input_file.name]

if len(sys.argv) > 1:
    files = sys.argv[1:]
else:
    files = os.listdir()

for file in files:
    if not file.endswith('.nsx'):
        continue

    nsx = zipfile.ZipFile(file)
    config_data = json.loads(nsx.read('config.json').decode('utf-8'))

    for notebook in config_data['notebook']:
        notebook_data = json.loads(nsx.read(notebook).decode('utf-8'))

        if notebook_data['title']:
            notebook_title = notebook_data['title']
        else:
            notebook_title = 'Untitled'

        print('Converting notebook "{}"'.format(notebook_title))

        if os.path.isdir(notebook_title):
            notebook_title = str(round(time.time())) + '-' + notebook_title

        os.makedirs(notebook_title + os.sep + media_dir)

        for note in config_data['note']:
            note_data = json.loads(nsx.read(note).decode('utf-8'))
            note_title = note_data['title']
            note_ctime = note_data.get('ctime', '')
            note_mtime = note_data.get('mtime', '')

            if note_data['parent_id'] != notebook:
                continue

            content = re.sub('<img class="syno-notestation-image-object" src=[^>]*ref="',
                             '<img src="', note_data.get('content', ''))

            with open(input_file.name, 'w', encoding='utf-8') as input_text:
                input_text.write(content)

            pandoc = subprocess.Popen(pandoc_args)
            pandoc.wait(5)

            with open(output_file.name, 'r') as output_text:
                content = output_text.read()

            attachment_list = []

            for attachment in note_data.get('attachment', ''):

                ref = note_data['attachment'][attachment].get('ref', '')
                md5 = note_data['attachment'][attachment]['md5']
                name = note_data['attachment'][attachment]['name']

                try:
                    nsx.extract('file_' + md5, notebook_title + os.sep + media_dir)
                except Exception:
                    print('  Can\'t find attachment "{}" of note "{}"'.format(name, note_title))
                    attachment_list.append('[NOT FOUND]([{}{}/{})'.format(link_prepend, media_dir, name))
                else:
                    if os.path.isfile('{}/{}/{}'.format(notebook_title, media_dir, name)):
                        name = str(round(time.time())) + '-' + name

                    os.rename('{}/{}/file_{}'.format(notebook_title, media_dir, md5),
                              '{}/{}/{}'.format(notebook_title, media_dir, name))
                    attachment_list.append('[{}]([{}{}/{})'.format(name, link_prepend, media_dir, name))

                if ref:
                    content = content.replace(ref, '{}{}/{}'.format(link_prepend, media_dir, name))

            if note_data.get('tag', '') or attachment_list or insert_title or insert_ctime or insert_mtime:
                content = '\n' + content

            if insert_mtime and note_mtime:
                text_mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_mtime))
                content = 'Modified: {}  \n{}'.format(text_mtime, content)
            if insert_ctime and note_ctime:
                text_ctime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_ctime))
                content = 'Created: {}  \n{}'.format(text_ctime, content)
            if attachment_list:
                content = 'Attachments: {}  \n{}'.format(' '.join(attachment_list), content)
            if note_data.get('tag', ''):
                content = 'Tags: {}  \n{}'.format(', '.join(note_data['tag']), content)
            if insert_title:
                content = note_title + '\n' + ('=' * len(note_title)) + '\n' + content

            if creation_date_in_filename and note_ctime:
                note_title = time.strftime('%Y-%m-%d ', time.localtime(note_ctime)) + note_title

            if platform.system() == 'Linux' and not force_windows_filename_limitations:
                md_file_name = note_title.replace('/', '-')
            elif platform.system() == 'Darwin' and not force_windows_filename_limitations:
                md_file_name = note_title.replace('/', '-').replace(':', '-')
            else:
                md_file_name = note_title
                for char in (':', '/', '\\', '|'):
                    md_file_name = md_file_name.replace(char, '-')
                for char in ('?', '*'):
                    md_file_name = md_file_name.replace(char, '')
                md_file_name = md_file_name.replace('<', '(')
                md_file_name = md_file_name.replace('>', ')')
                md_file_name = md_file_name.replace('"', "'")

            if note_title != md_file_name:
                print('  Note "{}" saved as "{}.{}" for compatibility with your OS'.format(note_title, md_file_name, md_file_ext))

            with open('{}/{}.{}'.format(notebook_title, md_file_name, md_file_ext), 'w') as md_note:
                md_note.write(content)

        try:
            os.rmdir(notebook_title + os.sep + media_dir)
        except OSError:
            pass

input_file.close()
output_file.close()
os.unlink(input_file.name)
os.unlink(output_file.name)

input('Conversion finished. Press Enter to quit...')

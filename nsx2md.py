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
import urllib.request

from pathlib import Path
from urllib.parse import unquote


# You can adjust some setting here.  Default is for QOwnNotes app. 

## 选择元数据选项
meta_data_in_yaml = True  # 若为 True，YAML 前置块将包含以下元数据项。   
                           # 若为 False，下方选中的元数据选项将置于 Markdown 文本中
insert_title = True  # 若为 True，将在 YAML 块中添加笔记标题字段；若为 False，则不在块中包含标题
insert_ctime = True  # 若为 True，将在 YAML 块中插入笔记创建时间；若为 False，则禁用
insert_mtime = True  # 若为 True，将在 YAML 块中插入笔记修改时间；若为 False，则禁用
tags = True  # 若为 True，将插入标签列表；若为 False，则禁用
tag_prepend = ''  # 在笔记内标签列表中为每个标签添加的前缀字符串，默认为空
tag_delimiter = ', '  # 分隔标签的字符串，默认为逗号分隔列表
no_spaces_in_tags = False  # 若为 True，将标签名称中的空格替换为 '_'；若为 False，则保留空格

## 选择文件链接选项
prepend_links_with = ''  # 为文件链接添加预设字符串前缀（例如 'file://'），'' 表示不添加前缀
encode_links_as_uri = True  # 使用“百分比编码”对链接中的特殊字符进行编码
                            # True 对应 "/link%20target" 样式链接，False 对应 "/link target" 样式链接
absolute_links = False  # 若为 True，使用绝对链接；若为 False，使用相对链接

## 选择文件/附件/媒体选项
media_dir_name = 'media'  # 在生成的目录中用于存储所有图像和附件的子目录名称
md_file_ext = 'md'  # 生成的 Markdown 语法笔记文件的扩展名
creation_date_in_filename = False  # 若为 True，将笔记创建时间插入笔记文件名；若为 False，则禁用

## Pandoc markdown options (read the pandoc documentation before tweaking)
pandoc_markdown_options = ['markdown_strict+pipe_tables-raw_html', '--wrap=none']


############################################################################

Notebook = collections.namedtuple('Notebook', ['path', 'media_path'])


def sanitise_path_string(path_str, max_bytes=200):
    """
    Sanitize path string and ensure it doesn't exceed max_bytes in UTF-8 encoding.
    Default max_bytes is 200 to leave room for parent path and extension.
    """
    path_str = urllib.parse.unquote(path_str)

    for char in (':', '/', '\\', '|'):
        path_str = path_str.replace(char, '-')
    for char in ('? ', '*'):
        path_str = path_str.replace(char, '')
    path_str = path_str.replace('<', '(')
    path_str = path_str.replace('>', ')')
    path_str = path_str.replace('"', "'")

    # Ensure the string doesn't exceed max_bytes when encoded as UTF-8
    encoded = path_str.encode('utf-8')
    if len(encoded) > max_bytes:
        # Truncate byte by byte to avoid cutting in the middle of a multi-byte character
        encoded = encoded[:max_bytes]
        # Decode and ignore errors at the end (in case we cut a multi-byte char)
        path_str = encoded.decode('utf-8', errors='ignore')
        # Remove trailing whitespace that might result from truncation
        path_str = path_str.rstrip()
    
    return path_str


def safe_file_path(base_path, file_name, extension):
    """
    Create a safe file path that won't exceed filesystem limits.
    Handles conflicts by adding numeric suffixes.
    """
    # Calculate max bytes for filename (255 bytes total - extension - dot - some margin)
    max_filename_bytes = 240 - len(extension.encode('utf-8'))
    
    sanitised_name = sanitise_path_string(file_name, max_bytes=max_filename_bytes)
    
    if not sanitised_name:
        sanitised_name = 'Untitled'
    
    file_path = Path(base_path / f'{sanitised_name}.{extension}')
    
    n = 1
    while file_path.is_file():
        # Account for the suffix length in bytes
        suffix = f'_{n}'
        suffix_bytes = len(suffix.encode('utf-8'))
        adjusted_max = max_filename_bytes - suffix_bytes
        
        truncated_name = sanitise_path_string(file_name, max_bytes=adjusted_max)
        file_path = Path(base_path / f'{truncated_name}{suffix}.{extension}')
        n += 1
        
        # Safety break to avoid infinite loops
        if n > 10000:
            # Use a hash-based name as last resort
            import hashlib
            hash_name = hashlib.md5(file_name.encode('utf-8')).hexdigest()[:16]
            file_path = Path(base_path / f'{hash_name}.{extension}')
            break
    
    return file_path


def create_yaml_meta_block():
    yaml_block = '---\n'

    if insert_title:
        yaml_block = '{}Title: "{}"\n'.format(yaml_block, note_title)

    if insert_ctime and note_ctime:
        yaml_text_ctime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_ctime))
        yaml_block = '{}Created: "{}"\n'.format(yaml_block, yaml_text_ctime)

    if insert_mtime and note_mtime:
        yaml_text_mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_mtime))
        yaml_block = '{}Modified: "{}"\n'.format(yaml_block, yaml_text_mtime)

    if tags and note_data.get('tag', ''):
        if no_spaces_in_tags: 
            note_data['tag'] = [tag.replace(' ', '_') for tag in note_data['tag']]
        yaml_tag_list = tag_delimiter.join(''.join((tag_prepend, tag)) for tag in note_data['tag'])
        yaml_block = '{}Tags: [{}]\n'.format(yaml_block, yaml_tag_list)

    yaml_block = '{}---\n'.format(yaml_block)
    
    if attachment_list:
        yaml_block = '{}\nAttachments:  {}\n'.format(yaml_block, ', '.join(attachment_list))
    
    return yaml_block


def create_text_meta_block():
    text_block = ''
    
    if insert_mtime and note_mtime: 
        text_mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_mtime))
        text_block = 'Modified: {}  \n{}'.format(text_mtime, text_block)
        
    if insert_ctime and note_ctime:
        text_ctime = time.strftime('%Y-%m-%d %H:%M', time.localtime(note_ctime))
        text_block = 'Created: {}  \n{}'.format(text_ctime, text_block)
        
    if attachment_list:
        text_block = 'Attachments: {}  \n{}'.format(', '.join(attachment_list), text_block)
        
    if note_data.get('tag', '') and tags:
        if no_spaces_in_tags:
            note_data['tag'] = [tag.replace(' ', '_') for tag in note_data['tag']]
        tag_list = tag_delimiter.join(''.join((tag_prepend, tag)) for tag in note_data['tag'])
        text_block = 'Tags: {}  \n{}'.format(tag_list, text_block)
    
    if insert_title:
        text_block = '{}\n{}\n{}'.format(note_title, '=' * len(note_title), text_block)
    
    return text_block


work_path = Path.cwd()
media_dir_name = sanitise_path_string(media_dir_name)
pandoc_input_file = tempfile.NamedTemporaryFile(delete=False)
pandoc_output_file = tempfile.NamedTemporaryFile(delete=False)


if not shutil.which('pandoc') and not os.path.isfile('pandoc'):
    print('Can\'t find pandoc.  Please install pandoc or place it to the directory, where the script is.')
    exit(1)

pandoc_args = ['pandoc', '-f', 'html', '-t', *pandoc_markdown_options, '-o',
               pandoc_output_file.name, pandoc_input_file.name]

if len(sys.argv) > 1:
    files_to_convert = [Path(path) for path in sys.argv[1:]]
else:
    files_to_convert = list(Path(work_path).glob('*.nsx'))

if not files_to_convert:
    print('No .nsx files found')
    exit(1)

for file in files_to_convert:
    nsx_file = zipfile.ZipFile(str(file))
    config_data = json.loads(nsx_file.read('config.json').decode('utf-8'))
    notebook_id_to_path_index = {}

    recycle_bin_path = work_path / Path('Recycle bin')

    n = 1
    while recycle_bin_path.is_dir():
        recycle_bin_path = work_path / Path('{}_{}'.format('Recycle bin', n))
        n += 1

    recycle_bin_media_path = recycle_bin_path / media_dir_name
    recycle_bin_media_path.mkdir(parents=True)
    notebook_id_to_path_index['1027_#00000000'] = Notebook(recycle_bin_path, recycle_bin_media_path)

    print('Extracting notes from "{}"'.format(file.name))

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

    note_id_to_title_index = {}
    converted_note_ids = []

    for note_id in config_data['note']:
        try:
            note_data = json.loads(nsx_file.read(note_id).decode('utf-8'))
        except KeyError:
            print('No text for {}. It may be an encrypted note not included in the .nsx file.'.format(note_id))
            continue

        note_title = note_data.get('title', 'Untitled')
        note_ctime = note_data.get('ctime', '')
        note_mtime = note_data.get('mtime', '')

        note_id_to_title_index[note_id] = note_title

        try:
            parent_notebook_id = note_data['parent_id']
            parent_notebook = notebook_id_to_path_index[parent_notebook_id]
        except KeyError:
            continue

        print('Converting note "{}"'.format(note_title))
        
        content = note_data.get('content', '')
        
        content = re.sub(r'<iframe[^>]*www\. youtube\.com/watch\?v=(\w+)[^/]*</iframe>',
                         r'<a href=\"https://www.youtube.com/watch?v=\1\">'
                         r'<img src=\"https://img.youtube.com/vi/\1/mqdefault.jpg\"></a>', 
                         content)

        content = re.sub(r'<img [^>]*ref=([^ ]*)[^>]*class=[^ ]*syno-notestation-image-object[^>]*>|'
                         r'<img [^>]*class=[^>]*syno-notestation-image-object[^>]*ref=([^ ]*)[^>]*>',
                         r'<img src=\1\2>', content)
        
        Path(pandoc_input_file.name).write_text(content, 'utf-8')
        pandoc = subprocess.Popen(pandoc_args)
        pandoc.wait(20)
        content = Path(pandoc_output_file.name).read_text('utf-8')
        
        if '[TABLE]' in content:
            print('    Unconverted table found. Tweaking pandoc options inside the script may (or may not) allow to convert it.')

        attachments_data = note_data.get('attachment')
        attachment_list = []

        if attachments_data: 
            for attachment_id in note_data.get('attachment', ''):

                ref = note_data['attachment'][attachment_id].get('ref', '')
                md5 = note_data['attachment'][attachment_id]['md5']
                source = note_data['attachment'][attachment_id].get('source', '')
                name = sanitise_path_string(note_data['attachment'][attachment_id]['name'])
                name = name.replace('ns_attach_image_', '')

                if note_data['attachment'][attachment_id].get('type', '') == 'application/octet-stream':
                    print("  The note has unsupported 'application/octet-stream' attachment '{}'".format(name))

                name_parts = name.rpartition('.')

                n = 1
                while Path(parent_notebook.media_path / name).is_file():
                    name = ''.join((name_parts[0], '_{}'.format(n), name_parts[1], name_parts[2]))
                    n += 1

                
                if absolute_links:
                    link_path = str(Path(parent_notebook.media_path / name))
                else:
                    link_path = '{}/{}'.format(media_dir_name, name)
                
                if encode_links_as_uri:
                    link_path = urllib.request.pathname2url(link_path).replace('///', '')
                    
                if prepend_links_with:
                    link_path = ''.join((prepend_links_with, link_path))
                
                
                try:
                    Path(parent_notebook.media_path / name).write_bytes(nsx_file.read('file_' + md5))
                    attachment_link = '[{}]({})'.format(name, link_path)
                except Exception: 
                    if source:
                        attachment_link = '[{}]({})'.format(name, source)
                    else:
                        print('Can\'t find attachment "{}" of note "{}"'.format(name, note_title))
                        attachment_link = '[NOT FOUND]({})'.format(link_path)


                if ref and source:
                    content = content.replace(ref, source)
                elif ref:
                    content = content.replace(ref, link_path)
                else: 
                    attachment_list.append(attachment_link)


        if note_data.get('tag', '') or attachment_list or insert_title \
                or insert_ctime or insert_mtime: 
            content = '\n' + content


        if meta_data_in_yaml:
            content = '{}\n{}'.format(create_yaml_meta_block(), content)
        else:
            content = '{}\n{}'.format(create_text_meta_block(), content)


        if creation_date_in_filename and note_ctime:
            note_title = time.strftime('%Y-%m-%d ', time.localtime(note_ctime)) + note_title


        # Use the new safe_file_path function
        md_file_path = safe_file_path(parent_notebook.path, note_title, md_file_ext)

        md_file_path.write_text(content, 'utf-8')

        converted_note_ids.append(note_id)

    for notebook in notebook_id_to_path_index.values():
        try:
            notebook.media_path.rmdir()
        except OSError:
            pass

    not_converted_note_ids = set(note_id_to_title_index.keys()) - set(converted_note_ids)

    if not_converted_note_ids:
        print('Failed to convert notes:',
              '\n'.join(('    {} (ID: {})'.format(note_id_to_title_index[note_id], note_id)
                         for note_id in not_converted_note_ids)),
              sep='\n')

    if len(config_data['notebook']) == 1:
        notebook_log_str = 'notebook'
    else:
        notebook_log_str = 'notebooks'

    print('Converted {} {} and {} out of {} notes.\n'.format(len(config_data['notebook']),
                                                             notebook_log_str,
                                                             len(converted_note_ids),
                                                             len(note_id_to_title_index.keys())))
    try:
        recycle_bin_media_path.rmdir()
    except OSError:
        pass

    try:
        recycle_bin_path.rmdir()
    except OSError:
        pass

pandoc_input_file.close()
pandoc_output_file.close()
os.unlink(pandoc_input_file.name)
os.unlink(pandoc_output_file.name)

input('Press Enter to quit...')
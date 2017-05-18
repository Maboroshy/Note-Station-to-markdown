#!/usr/bin/env python

import os
import re
import sys 
import time
import json
import zipfile
import subprocess

# You can adjust some setting here. Default is for QOwnNotes app.
link_prepend = 'file://'
media_dir = 'media'
md_file_ext = 'md'


try:
    subprocess.Popen(['pandoc', '-v'], stdout=subprocess.DEVNULL)
except Exception:
    print('Can\'t find pandoc. Please install pandoc or place it to the directory, where the script is.') 
    exit()
    
if len(sys.argv) > 1:
    files=sys.argv[1:]
else:
    files = os.listdir()

for file in files:
    if not file.endswith('.nsx'):
        continue
    
    nsx = zipfile.ZipFile(file)
    config_data = json.loads(nsx.read('config.json'))
    
    for notebook in config_data['notebook']:
        notebook_data = json.loads(nsx.read(notebook))
        
        if notebook_data['title']:
            notebook_title = notebook_data['title']
        else:
            notebook_title = 'Untitled'
        
        print('Converting notebook "{}"'.format(notebook_title))
        
        if os.path.isdir(notebook_title):
            notebook_title = str(round(time.time())) + '-' + notebook_title
            
        os.makedirs(notebook_title + '/' + media_dir)
        
        for note in config_data['note']:
            note_data = json.loads(nsx.read(note))
            note_title = note_data['title']
            
            if note_data['parent_id'] == notebook:
                content = re.sub('<img class="syno-notestation-image-object" src=[^>]*ref="', 
                                    '<img src="', note_data['content'])
                
                pandoc = subprocess.Popen(['pandoc', '-f', 'html', 
                                                     '-t', 'markdown_strict+pipe_tables-raw_html', 
                                                     '--wrap=none'], 
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                content = pandoc.communicate(input=content.encode('utf-8'))[0].decode('utf-8')
                
                attachment_list = []
                
                for attachment in note_data.get('attachment', ''):
                    
                    ref = note_data['attachment'][attachment].get('ref', '')
                    md5 = note_data['attachment'][attachment]['md5']
                    name = note_data['attachment'][attachment]['name']
                    
                    try:
                        nsx.extract('file_' + md5, notebook_title + '/' + media_dir)
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
                        content = content.replace(ref,'{}{}/{}'.format(link_prepend, media_dir, name))
                    
                if note_data['tag'] or attachment_list:
                    content = '\n' + content
                    
                    if attachment_list:
                        content = 'Attachments: {}\n{}'.format(' '.join(attachment_list), content)                             
                    if note_data['tag']:
                        content = 'Tags: {}\n{}'.format(', '.join(note_data['tag']), content)
                
            md_note = open('{}/{}.{}'.format(notebook_title, note_title, md_file_ext), 'w')
            md_note.write(content)
            md_note.close
        
        try:
            os.rmdir(notebook_title + '/' + media_dir)
        except OSError:
            pass
        
input('Conversion finished. Press Enter to quit...')

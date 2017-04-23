#!/bin/bash

# You can adjust some setting here. Default is for QOwnNotes app.
link_prepend='file://'
media_dir='media'
md_file_ext='md'


IFS=$'\n'

# Check dependencies
hash 'unzip' || { printf '%s\n' "Can't find 'unzip' binary. Please install 'unzip' package."; exit; } 
hash 'jq' || { printf '%s\n' "Can't find 'jq' binary. Please install 'jq' package."; exit ; }
hash 'pandoc' || { printf '%s\n' "Can't find 'pandoc' binary. Please install 'pandoc' package."; exit; } 

# If there's a command line argument, run the script for specified nsx file exclusively.
if [[ -n $1 ]]; then 
    nsx_files=$1
    [[ -d ${1%\/*} ]] && cd "${1%\/*}"
else nsx_files="$(find "$(pwd)" -maxdepth 1 -name "*.nsx" -type f)"
fi

# Process nsx files.
for nsx in $nsx_files; do
    
    unzip -q $nsx -d 'temp'
    
    # Get json file name with notebook data.
    notebook_list="$(jq -r '.notebook[]' 'temp/config.json')"
    [[ -z $notebook_list ]] \
        && printf '%s\n' "Can't find notebook data. Maybe the nsx file is broken or incomplete." && exit
    
    for notebook_json in $notebook_list; do
        
        # Get notebook title from notebook json.
        notebook_name="$(jq -r '.title' "temp/$notebook_json")"
        [[ -z $notebook_name ]] && notebook_name="${nsx%.nsx}-$RANDOM"
        mkdir -p $notebook_name/$media_dir
        
        # Get all notes json file names.
        note_list="$(jq -r '.note[]?' 'temp/config.json')"
        
        # Get data from each note json.
        for note in $note_list; do
            
            # Check if note is in the processed notebook.
            [[ "$(jq -r '.parent_id' "temp/$note")" != "$notebook_json" ]] && continue
            
            title="$(jq -r '.title' "temp/$note")"
            tag="$(jq -r '.tag[]?' "temp/$note" | tr '\n' ',')"
            tag="${tag%,}"
            
            # Convert content from html to markdown.
            content="$(jq -r '.content' "temp/$note" | \
                sed 's|<img class="syno-notestation-image-object" src=[^>]*ref="|<img src="|g' | \
                pandoc -f html -t markdown_strict+pipe_tables-raw_html --wrap=none)"
            
            # Get attachments data.
            attachment_list=
            attachments="$(jq -c '.attachment[]?' "temp/$note")"
            for key in $attachments; do
                ref="$(printf '%s' "$key" | jq '.ref' | tr -d '"')"
                md5="$(printf '%s' "$key" | jq '.md5' | tr -d '"')"
                name="$(printf '%s' "$key" | jq '.name' | tr -d '"')"
                
                # Copy attachment files to media directory.
                if [[ -f temp/file_$md5 ]]; then
                    [[ -f $media_dir/$name ]] && name="$name-$RANDOM"
                    cp -f "temp/file_$md5" "$notebook_name/$media_dir/$name"
                else printf '%s\n' "Can't find attachment \"$name\" of note \"$title\"."
                fi
                
                # Change links in the note accordingly.
                [[ ref != 'null' ]] && content="${content//$ref/$link_prepend$media_dir\/$name}"
                attachment_list+="[$name]($link_prepend$media_dir/$name) "
            done
            
            # Add attachments list to the beginning of the note.
            [[ -n $attachment_list ]] && content="$(printf '%s\n\n%s' "Attachments: $attachment_list" "$content")"
            
            # Write markdown file.
            printf '%s' "$content" > "$notebook_name/[$tag] $title.$md_file_ext"
        done
        
        # Delete media directory if no files have been moved there, and it's empty.
        rm -d "$notebook_name/$media_dir" 2> /dev/null 
    done
    
    rm -rf 'temp'
done

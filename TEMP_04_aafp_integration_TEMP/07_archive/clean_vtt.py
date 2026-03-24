import os
import re

def vtt_to_txt(directory):
    output_folder_name = "converted_txt_files"
    output_path = os.path.join(directory, output_folder_name)
    os.makedirs(output_path, exist_ok=True)
    print(f"Files will be saved to: {output_path}\n")

    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}')
    
    for filename in os.listdir(directory):
        if filename.endswith(".vtt"):
            vtt_path = os.path.join(directory, filename)
            txt_filename = os.path.splitext(filename)[0] + ".txt"
            txt_path = os.path.join(output_path, txt_filename)
            
            with open(vtt_path, "r", encoding="utf-8") as vtt_file:
                lines = vtt_file.readlines()
            
            final_text_blocks = []
            current_sentence = []

            for line in lines:
                clean_line = line.strip()

                # --- STEP 1: REMOVE VTT JUNK ---
                if "WEBVTT" in clean_line: continue
                if timestamp_pattern.search(clean_line): continue
                if clean_line.isdigit(): continue
                if clean_line == "": continue
                
                # --- STEP 2: REMOVE TAGS & SOUND CUES ---
                # Remove HTML-style tags (e.g., <v ->, </v>, <i>)
                clean_line = re.sub(r'<[^>]+>', '', clean_line)
                # Remove items in parentheses (e.g., (upbeat music))
                clean_line = re.sub(r'\([^\)]+\)', '', clean_line)
                # Remove items in brackets (e.g., [sound])
                clean_line = re.sub(r'\[[^\]]+\]', '', clean_line)
                
                # If the line is empty after cleaning, skip it
                if not clean_line.strip(): continue

                # --- STEP 3: BUILD SENTENCES ---
                current_sentence.append(clean_line.strip())

                if clean_line.strip().endswith(('.', '?', '!')):
                    full_sentence = " ".join(current_sentence)
                    # Fix double spaces that might occur after removing tags
                    full_sentence = re.sub(r'\s+', ' ', full_sentence)
                    final_text_blocks.append(full_sentence)
                    current_sentence = []

            # Catch leftovers
            if current_sentence:
                full_sentence = " ".join(current_sentence)
                full_sentence = re.sub(r'\s+', ' ', full_sentence)
                final_text_blocks.append(full_sentence)

            with open(txt_path, "w", encoding="utf-8") as txt_file:
                # Join with double newlines for readable paragraphs
                txt_file.write("\n\n".join(final_text_blocks))
            
            print(f"Cleaned & Formatted: {filename}")

if __name__ == "__main__":
    current_directory = os.getcwd()
    vtt_to_txt(current_directory)
from .utils.replace import img_replace
from PIL import Image
import glob
import io
import os
import pymupdf
import re
import shutil
from send2trash import send2trash

"""
Auto-inject images into a pdf scan based on filenames

Example:
    my_doc.pdf
    my_doc p0001.png
    my_doc p0020.png

For the above file structure, run:

    pdfscantools-inject my_doc.pdf "my_doc p0001.png" "my_doc p0020.png"

or, to autodetect images:

    pdfscantools-inject my_doc.pdf

The page number is implied from the end of the filename,
and replaces whatever image was on that page originally.
New image sizes are resized based on the original dimensions.
"""

def get_img_page(img_path):
    """
    Extract page index embedded in filename
    """
    filepath, filename = os.path.split(img_path)
    page_text = re.split(r'\W+', filename)[-2]
    page_text = re.sub("[^0-9]", "", page_text)
    try:
        page = int(page_text)
    except Exception as e:
        print(e)
        return -1
    return page

def get_inject_image_paths(doc_path):
    basename = doc_path.replace(".pdf", "")
    glob_path = f"{basename}*"
    paths = glob.glob(glob_path)
    paths.remove(doc_path)
    return paths

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("doc_path", help="Path to doc to inject images into")
    parser.add_argument("img_paths", nargs="?", help="Images to inject into doc")
    parser.add_argument("--dry", action="store_true", help="Print results but don't modify anything")
    parser.add_argument("--backup", action="store_true", help="Rename and keep original copy rather than overwriting it")
    args = parser.parse_args()

    # Load doc
    doc = pymupdf.open(args.doc_path, filetype="pdf")
    doc_base, doc_ext = os.path.splitext(args.doc_path)

    if(not args.img_paths):
        args.img_paths = get_inject_image_paths(args.doc_path)
    
    if(not args.img_paths):
        print("No images to inject! Exitting")
        exit(0)

    for img_path in args.img_paths:
        page_num = get_img_page(img_path)

        if(page_num == -1):
            print(f"Failed to parse page number from filename '{img_path}'")
            continue

        if(page_num == 0):
            print(f"Failed to use image page num. Number pages starting with 1, not 0. '{img_path}'")
            continue

        page_num -= 1

        # Find target page
        page = doc[page_num]
        page_img = page.get_images()[0]
        page_img_info = page.get_image_info()[0]
        #print(page_img_info)

        print(f"Replacing img on page {page_num} with '{img_path}'")

        # resize img to original pdf img size 
        repl_img = Image.open(img_path)
        repl_img = repl_img.resize([page_img_info['width'], page_img_info['height']])
        repl_img_io = io.BytesIO()
        repl_img.save(repl_img_io, "jpeg")

        img_replace(page, page_img[0],
            stream=repl_img_io,
        )
    
    # Write it out
    doc_backup_path = f"{doc_base}.bak{doc_ext}"

    print(f"Copy original {args.doc_path} -> {doc_backup_path}")
    if(not args.dry):
        shutil.copy(args.doc_path, doc_backup_path)

    print(f"Save -> {args.doc_path}")
    if(not args.dry):
        if(not doc.can_save_incrementally()):
            print("ERR CANT SAVE INCREMENTALLY.")
        else:
            doc.save(
                args.doc_path, 
                incremental=True, 
                encryption=pymupdf.PDF_ENCRYPT_KEEP
            )

    print(f"Trashing original -> {doc_backup_path}")
    if(not args.dry):
        for img in args.img_paths:
            send2trash(img)
        if(not args.backup):
            send2trash(doc_backup_path)

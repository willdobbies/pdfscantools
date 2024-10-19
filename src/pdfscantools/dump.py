import pymupdf
import fitz
import os

"""
Dump all image files contained within pdf scan, convert to png
Assumes 1 image per-page
"""

def recoverpix(doc, item):
    xref = item[0]  # xref of PDF image
    smask = item[1]  # xref of its /SMask

    # special case: /SMask or /Mask exists
    if smask > 0:
        pix0 = fitz.Pixmap(doc.extract_image(xref)["image"])
        if pix0.alpha:  # catch irregular situation
            pix0 = fitz.Pixmap(pix0, 0)  # remove alpha channel
        mask = fitz.Pixmap(doc.extract_image(smask)["image"])

        try:
            pix = fitz.Pixmap(pix0, mask)
        except Exception as e:  # fallback to original base image in case of problems
            print(e)
            pix = fitz.Pixmap(doc.extract_image(xref)["image"])

        if pix0.n > 3:
            ext = "pam"
        else:
            ext = "png"

        return {  # create dictionary expected by caller
            "ext": ext,
            "colorspace": pix.colorspace.n,
            "image": pix.tobytes(ext),
        }

    # special case: /ColorSpace definition exists
    # to be sure, we convert these cases to RGB PNG images
    if "/ColorSpace" in doc.xref_object(xref, compressed=True):
        pix = fitz.Pixmap(doc, xref)
        pix = fitz.Pixmap(fitz.csRGB, pix)
        return {  # create dictionary expected by caller
            "ext": "png",
            "colorspace": 3,
            "image": pix.tobytes("png"),
        }
    return doc.extract_image(xref)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("doc_path", help="Path to doc to inject images into")
    parser.add_argument("--dry", action="store_true", help="Print results but don't modify anything")
    args = parser.parse_args()

    # Load doc
    doc = pymupdf.open(args.doc_path, filetype="pdf")

    doc_base, doc_ext = os.path.splitext(args.doc_path)

    xreflist = []
    image_list = []
    for page_num in range(doc.page_count):
        il = doc.get_page_images(page_num)
        image_list.extend([x[0] for x in il])

        for img in il:
            xref = img[0]
            if xref in xreflist:
                continue
            image = recoverpix(doc, img)
            imgdata = image["image"]
            imgfile = os.path.join(f"{doc_base} p%03i.%s" % (page_num+1, image["ext"]))
            print(f"Got image '{imgfile}'")

            if(args.dry):
                continue

            fout = open(imgfile, "wb")
            fout.write(imgdata)
            fout.close()
            xreflist.append(xref)

    imglist = list(set(image_list))
    print(len(set(imglist)), "images in total")
    print(len(xreflist), "images extracted")
> For Chinese version, please see: [README_chi.md](README_chi.md)  
> English version's README is translated by ChatGPT


# PDF Fake-Landscape Geometry Fix Tool

A PDF geometry normalization tool designed to diagnose and repair
Fake-Landscape PDF pages caused by incorrect /Rotate metadata and broken
Page / Annotation / Stamp coordinate synchronization.

---

## Features & Usage

### Features

![Screenshot](Totur/pciture/Screenshot1.png)

This tool diagnoses and repairs the following PDF geometry problems:

- Fake-Landscape pages caused by incorrect /Rotate metadata  
- Desynchronized Page / Annotation / Stamp coordinate systems  
- Mixed-orientation PDFs (partially correct, partially broken)

---

### Basic Usage

1. Upload your PDF  
2. Click Upload PDF to load the document  
3. Click Analyze to view geometry diagnostics  
4. Click Fix PDF to download the normalized file  

---

## Installation & Tech Stack

### Setup
```
pip install fastapi uvicorn pypdf python-multipart
```
---

### Run
```
uvicorn server:app --reload
```
or simply:

run.bat

Open browser:
```
http://127.0.0.1:8000
```
---

### Tech Stack

| Technology | Version |
|------------|---------|
| Python | 3.13 |
| FastAPI | 0.128.0 |
| Uvicorn | 0.40.0 |
| pypdf | 6.1.0 |
| python-multipart | 0.0.21 |

---

## Background

This project originated from a real-world need to batch-stamp thousands of PDF documents. Manual processing was impractical, so a Python + AI solution was attempted.

During early automation, stamp positions appeared inconsistent on certain pages. Further diagnostics revealed the presence of Fake-Landscape pages, which are actually Portrait pages with a residual /Rotate=270 flag.

The problem was therefore decomposed into:

- Page orientation normalization  
- Stamp coordinate normalization  

A lightweight Web UI was later built to improve usability and maintainability.

Stamping functionality is currently under integration.

---

## Geometry Notes

### Geometry Layers

PDF rendering geometry consists of three independent semantic layers:

- Page world (global coordinate system)  
- Annotation Rect world (interactive layer)  
- Stamp local world (local drawing space)  

These layers do not automatically synchronize.

---

### Page Layer

Page geometry is defined by MediaBox and /Rotate.

Fake-Landscape pages contain physically rotated content but retain a /Rotate=270 logical flag.

The normalization procedure rewrites the Page world:
```
tf = Transformation().rotate(90).translate(h, 0)  
page.add_transformation(tf)  
page.mediabox = RectangleObject([0, 0, h, w])  
page.rotation = 0
```
---

### Annotation Layer

Annotation Rects do not automatically follow Page CTM changes.

Therefore all /Rect fields must be manually transformed using the same affine matrix.

---

### Stamp Layer

Stamp final rendering:

Final = PageCTM · ( StampLocalCTM · Geometry )

After PageCTM normalization:

Fina

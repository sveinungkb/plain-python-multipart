# plain-python-multipart

## Background

I was in need of a basic multipart HTTP request reader to process file uploads in [Circuitpython](https://docs.circuitpython.org/).
Requirements were low memory footprint (little/no buffering) since this will run on an ESP32 and no use of fancy Python APIs since Circuitpython only supports a basic subset.

This is by no means meant to be a full HTTP server implementation, just the minimal needed for a browser to upload files.

## License
Use however you wish, edit, clone, copy use as you want, but when possible leave a backlink to this repo so issues and changes can be incorporated upstream for everyone to take advantage.
> Copyright 2024 Sveinung Kval Bakken
> 
> Free for all use in any form.
> 
> https://github.com/sveinungkb/plain-python-multipart


## `server.py`
This is your test class, start with `python3 server.py`, you can `curl` a request to the endpoint printed at start, e.g:

```python
curl -vv --http1.0 http://127.0.0.1:65432/ -F "text=@loremipsum.txt" -F "image=@picsum.photos.jpg"
```

The uploaded files will be written with `.out` suffix and can be compared with the provided `.md5` checksums during testing.

## `multipart.py`
The main class, copy this to your project keeping the file header intact.
Change or replace the `FilePart` class to direct output where you would like, like streaming it to the [dualbank](https://docs.circuitpython.org/en/latest/shared-bindings/dualbank/index.html#module-dualbank) for OTA updates or `/CIRCUITPY` for app code updates.

## `loremipsum.txt`, `picsum.photos.jpg`
Test fixtures for text/binary file upload.

## Footnote

Image courtesy of [picsum.photos](https://picsum.photos).
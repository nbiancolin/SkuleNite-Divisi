# Musescore Processing

Understanding this code

Call format_mscz with a musescore mscz file.
-> This unzips the file, adds styles, and then processes each mscx file on its own

process_mscx is called with a mscx file
-> This goes through and does all of the formatting steps to the mscx file
the `if_standalone` thing is just for running it on its own with its own main function, for testing with uncompressed musescore files
-> Each processing step is listed under LayoutBreak Formatting
-> All of the "factories" and helpers to do the actual xml manipulation are above that

see https://github.com/nbiancolin/musescore-part-formatter-poc
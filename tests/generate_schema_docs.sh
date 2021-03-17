#!/bin/bash

DOC_OUTPUT="doc/build"
INDEX_FILE="${DOC_OUTPUT}/index.html"

cat > "${INDEX_FILE}" <<"EOF"
<!DOCTYPE html>
<html>
  <head>
    <title>Homer Public documentation</title>
  </head>
  <body>
    <h1>Configuration files</h1>
EOF

if [ ! -d $DOC_OUTPUT ]; then
  mkdir -p $DOC_OUTPUT;
fi

for file in tests/schemas/*.schema; do
    echo "Generating documentation for schema ${file}"
    name="$(basename "${file}")"
    generate-schema-doc "${file}" "${DOC_OUTPUT}/${name}.html"
    echo -e "<p><a href='${name}.html'>${name}</a></p>\n" >> "${INDEX_FILE}"
done


cat >> "${INDEX_FILE}" <<EOF
  </body>
</html>
EOF

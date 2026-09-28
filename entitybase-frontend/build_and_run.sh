echo "building using pack"
pack build --builder tools-harbor.wmcloud.org/toolforge/heroku-builder:22 myimage
echo "running using docker"
docker run -e PORT=8000 -p 8000:8000 --rm --entrypoint web myimage
echo "navigate to http://127.0.0.1:8000 to check that it works"
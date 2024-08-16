# imagehash-benchmark
Imagehash accuracy benchmarking repository

## Init repository
```
git clone git@github.com:Wikimedia-Suomi/imagehash-benchmark.git
python3 -m venv venv
source venv/bin/activate
pip install imagehash pywikibot django
```
## Init data
```
cd src
python manage.py makemigrations
python manage.py migrate
```
## Fetch sample images using petscan
```
python manage.py fetch_images
```
## Calculate imagehashes to database
```
python manage.py fetch_image_urls --hash_algorithms phash ahash dhash whash phash_simple phash_resize_first 
```
## Analyze imagehashes
```
python manage.py analyze_hashes --hash_algorithms phash ahash dhash whash phash_simple phash_resize_first
```
## Reset database
```
rm src/db.sqlite3
src/benchmark/migrations/00*.py
```

## Management commands
```
src/benchmark/management/commands/fetch_images.py
src/benchmark/management/commands/fetch_image_url.py
src/benchmark/management/commands/analyze_hashes.py
```


# Get total size of project or bucket

The python script will give you information about how many objects are in a project or bucket in google cloud storage and what 
are there total size.

How to run it
---

## Google cloud storage

Before running the script make sure that _Service Account_ file exists in `./settings` folder and that the file `./settings/static/Config.json` has a key with the same `project id` pointing to _Service Account_ file.

* Use switch `--server=gcs`

* To list size and number of all objects in a projects

    `$ python total_size.py --project_id=<name of project> --server=gcs`

* To list size and number of all objects in a buckets

    `$ python total_size.py --project_id=<name of project> --bucket_id=<name of the bucket> --server=gcs`

* If you want to control (increase or decrease) number of parallel threads, you should run

    `$ python total_size.py --project_id=<name of project> --max_thread=<a number less than 1001> --server=gcs`

## AWS S3

Before running the script make sure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set to correct value in `./settings/static/aws_keys.json`.

* Pass `--server=s3` in command line

* Use `--project_id=<name>` to identify the key in `./settings/static/aws_keys.json`

* To list size and number of all objects in all s3 buckets

    `$ python total_size.py --project_id=<name of key> --server=s3`

* To list size and number of all objects in a buckets

    `$ python total_size.py --project_id=<name of key> --bucket_id=<name of the bucket> --server=s3`
* If you want to control (increase or decrease) number of parallel threads, you should run

    `$ python total_size.py --project_id=<name of key> --max_thread=<a number less than 1001> --server=s3`

# BDKD Datastore

The BDKD Data Management Guide provides a guidance on how dataset and repositories can be arranged and managed under the BDKD system.

Consider the following setup:

![](images/datastore-setup-v2.png)

## Datastore
In the above, the BDKD Datastore is a conceptual term that refers to a storage solution that allows the BDKD system a technology to host data repositories that can handle very large amount of data. 

For example the BDKD project uses  Amazon Web Services’ (AWS) Simple Storage Solution (S3) as its datastore solution.

## Repositories
The datastore is used to host many data repositories, but each repository must be uniquely identifiable. In the case of AWS, each data repository is held in a single S3 bucket. 

So in the above example, for the 3 data repositories, we will set up 3 x S3 buckets:

```
s3://bdkd-geophysics-public
s3://bdkd-laser-public
s3://bdkd-ecology-public
```

The naming convention above is purely to indicate that the bucket is used for the BDKD project, and the data within are available to the public.

In each repository, researchers can publish many datasets relating to that data repository. 

For example geoscientists will publish their data into the “Geo Data Repository”, while laser physics researchers will upload their data into the “Laser Data Repository”.


## Datasets
A dataset  is a list of files (or URL links to files) that is being published together. Each dataset must be given a name that is unique to that repository so that it can be accurately accessed. 

A dataset in BDKD is made up of 2 key sections: 

1. the data files (or links to files) of that dataset
2. the meta data (such as author, data descriptions, etc) that provides information about that dataset (see below for more about meta data)


In the above example, there is a dataset called “XYZ rotations”. When accessing that dataset, users will be able to extract data from the files that is in that dataset to be used, as well as obtain meta information about that dataset, such as what type of data it is, and how to contact the person that published that data.

## Examples

Always use the in-line documentation via:
```
datastore-utils --help
```

### List available repositories
```
datastore-util repositories
```

### List available datasets on specific repository
```
datastore-util list bdkd-sirca-public
```

### Create a dataset
```
datastore-util create --no-publish "bdkd-sirca-public" "Coastlines-dataset" data/*
```

### Get metadata from a dataset
```
datastore-util get "bdkd-sirca-public" "Coastlines-dataset"
```

### Get files to local folder
```
datastore-util files "bdkd-sirca-public" "Coastlines-dataset"
```


## Notes on using AWS
When creating data repositories in AWS using S3 buckets, it is best if the S3 buckets are created in a same region as where your portals EC2 instances are launched in, as this will reduce the cost of operation without incurring unnecessary cross region charges.

When creating data repositories, make sure you provide read-access to the bucket for the portal IAM role.
If you have a cloud desktop instance that you used for uploading data into the repository, make sure you provide read/write access to the bucket for the cloud-desktop IAM role.

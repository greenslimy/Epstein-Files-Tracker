# Epstein File Tracker

The Epstein File Tracker is an on-going project to assist in the preservation of the public release of the Epstein Files.

You can find the public release of the documents [here](https://www.justice.gov/epstein/doj-disclosures).

Note: The live_links.csv file included in the initial release of this repository was pulled at 10PM CST on 2/2/2026. This contains many duplicated links, as that is how they were presented on the website. It does, however, contain all links that were publicly available across all datasets at the time.

## Usage

```shell
> python main.py -h
usage: main.py [-h] -o TRACKER_OUTPUT [-f EPSTEIN_FILES] [--paginate]

Epstein Files Tracker

options:
  -h, --help         show this help message and exit
  -o TRACKER_OUTPUT  Local location you would like output files to be written. Be sure to create a logs directory first!
                     Tracker will look here for input .csv files that were created by this program.
  -f EPSTEIN_FILES   Local location of your copy of the unzipped Epstein Files (Under construction)
  --paginate         Paginate and record links from the justice.gov live release of the files


> python main.py -o path/to/output -f path/to/files --paginate
```
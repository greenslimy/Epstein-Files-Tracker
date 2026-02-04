class Settings:

    live_paginated_base_url = 'https://www.justice.gov/epstein/doj-disclosures'
    live_files_base_url = 'https://www.justice.gov/epstein/files'
    local_files_base_url = None     #Populated by -f argument
    local_output_files_url = None   #Populated by -o argument
    download_missing_files = True   #If the file(s) scraped were not found locally, download them.

    dataset_count = 12
    dataset_pages = {   #Number of pages in each dataset. This is not easily identifiable programmatically, e.g. 9 rolls over to "create" more pages.
        1: 64,
        2: 12,
        3: 2,
        4: 4,
        5: 3,
        6: 1,
        7: 1,
        8: 221,
        9: 9397,
        10: 103,
        11: 16,
        12: 4
    }
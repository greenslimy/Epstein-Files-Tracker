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

    headers = {
        "sec-ch-ua": """"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24""",
        "sec-ch-ua-mobile":"?0",
        "sec-ch-ua-platform":"Windows",
        "upgrade-insecure-requests":"1",
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    }

    #Verify your age to access the Epstein files. This cookie is set when you click the "Yes, I am over 18" button on the justice.gov website. You can find it in your browser's developer tools under Application > Cookies.
    #This is required to view and download files from the website, and the program will not work without it. If you are running this program yourself, you will need to set this cookie in the Settings class to your own value. It may expire after some time, so if you start getting 403 errors, try updating this cookie.
    cookie = {
        "justiceGovAgeVerified": "true",
        "QueueITAccepted-SDFrts345E-V3_usdojsearch": "EventId%3Dusdojsearch%26RedirectType%3Dsafetynet%26IssueTime%3D1771055698%26Hash%3Df796f7bfc86822370dc5bc7afa993b5117ee934202dacbd845c7cfe9cded6bc7",
        "ak_bmsc": "F911AACDABD42B87FC69EE21D3E5100E~000000000000000000000000000000~YAAQDFPRFxQiqlKcAQAAHlQlWx7ioNAJUCoh6PuCsK2QtbmZdONejbpvkOgdJaydaPlnLIPTTRutB4/t1Dj64kEQTdGkUk92428EI3Gw7kmfmdMQKD19W11gMoRsyBJx15i3+yLuLMi51XnbDRWcR+Uz0a2WePXleaQdeA9pnsz6UnLdMIrgihPNSfEQWT49mdcnO4VvY8rQUTqZDKcyFEzhp33kOH6KrTaTMqX3pplWF6Qr26TulZqgSFPR+iGbMrjBsmiW0IIm9TfYGPrB8nwFOY0qMQLH1ExoOOYeBlTGKnmdCE2siUUbvYL0ShV908PJ4SmvepMHtfnIZOhVQWsZzFkybF9xD0afm76gljoEeMV52WH07YnhVmjQzubOwwBrBduYrnBhvQPYlw+G/uBZ+JLGnvK+Z6F8YGiCmrNb+gDMsLckunVDRx8A8uRVz54VisnxJtkL6lpBEAQ17W7cgacQ",
        "QueueITAccepted-SDFrts345E-V3_usdojfiles": "EventId%3Dusdojfiles%26RedirectType%3Dsafetynet%26IssueTime%3D1771055754%26Hash%3Dc88d8fd1ce6d564427a66e6126b81f60c0007f58469775fa0f89f8a092060581"
    }
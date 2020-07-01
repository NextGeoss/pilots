# pilots
Repository for the Pilots.
This repository contains the script for creating or updating Pilot information.

## How to run the script
1. Create a vritual env (Note: the script still uses python2)

  ```  virtualenv -p /path/to/python2 venv ```
  
2. Install the dependencies

  ``` pip install -r requirements.txt ```
  

3. Set up the information in the `credentials.ini` file
```
ckan_url = url to the ckan portal
ckan_api_token = sys admin API key
```

4. Run the script and follow the questions

``` python pilots_script.py ```

import requests

MONTH2NUMBER = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

# Element '0' is empty, because this needs to associate the month number as in MONTH2NUMBER
NUMBER2MESE = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

def getWeatherCsv(city, year, month, filename=None):
    """
    This program is used to download weather data.
    The input parameters are:
    - city: name of the city (str)
    - year: int/str
    - month: can be in italian, english (str) or number (int)
    - filename: (str) optional file name

    The function returns the file name
    """
    
    base_url = "https://www.ilmeteo.it/portale/archivio-meteo/"      #Torino/2018/Dicembre?format=csv

    cityname = city.capitalize()

    if isinstance(month, int):
        monthNum = month
        mese = NUMBER2MESE[month]
    elif isinstance(month, str):
        if month in MONTH2NUMBER.keys():
            monthNum = MONTH2NUMBER[month.capitalize()]
            mese = NUMBER2MESE[monthNum]
        elif month in NUMBER2MESE:
            monthNum = NUMBER2MESE.index(month.capitalize())
            mese = month
        else:
            raise ValueError("Invalid month!")
    else:
        raise ValueError("Invalid month!")
    
    anno = str(year)

    if filename is None:
        filename = "csv_ilMeteo/" + cityname + '-' + anno + '-' + str(monthNum).zfill(2) + mese + '.csv'
    
    full_url = base_url + cityname + '/' + anno + '/' + mese + '?format=csv'

    r = requests.get(full_url)

    content = r.content
    
    with open(filename, 'wb') as f:
        f.write(content)
        f.close()

    return filename


if __name__ == "__main__":
    getWeatherCsv("Torino", 2016, "May")

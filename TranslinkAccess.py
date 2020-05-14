import os
import numpy as np 
import pandas as pd
import requests
from xml.etree import ElementTree as et
import matplotlib.pyplot as plt
import seaborn as sns
import cv2

class TranslinkAPI:
    
    def __init__(self):
        
        self.KEY = 'gWS0uIIw4v4mT1rlKyJY'
        self.df_cols = [
        'StopNo',
        'Name',
        'BayNo',
        'City',
        'OnStreet',
        'AtStreet',
        'Latitude',
        'Longitude',
        'WheelchairAccess',
        'Distance',
        'Routes']
        self.LAT = (49.207891,49.288976)
        self.LONG = (-123.241625,-123.023505)
        self.busses = self.__get_response()
        self.coords = self.__prepare_data()
        self.plottedImage = self.__mapquest_access()
        self.__plot()
    
    def __parse_XML(xtree, df_cols): 
        """Parse the input XML file and store the result in a pandas 
        DataFrame with the given columns. 

        The first element of df_cols is supposed to be the identifier 
        variable, which is an attribute of each node element in the 
        XML data; other features will be parsed from the text content 
        of each sub-element. 
        """

        xroot = xtree.getroot()
        rows = []

        for node in xroot:
            res=[]
            for el in df_cols[0:]: 
                if node is not None and node.find(el) is not None:
                    res.append(node.find(el).text)
                else: 
                    res.append(None)
            rows.append({df_cols[i]: res[i] 
                         for i, _ in enumerate(df_cols)})

        out_df = pd.DataFrame(rows, columns=df_cols)

        return out_df 

    def __get_response(self):
        """Function for getting the response from the Translink API
        with the KEY embedded into the URL below. URL call uses longitude
        and latitude ranges and searches for bus stops within 2 km of each
        latitude and longitude coordinate pair."""
        
        if (os.path.exists('locationsdata.csv')):   

            latspace = np.linspace(self.LAT[0],self.LAT[1],20)
            longspace = np.linspace(self.LONG[0],self.LONG[0],20)   

            INIT=True
            for lat in latspace:
                for long in longspace:  
                    response = requests.get('https://api.translink.ca/rttiapi/v1/stops?apikey=gWS0uIIw4v4mT1rlKyJY&lat='+str(lat)[0:7]+'&long='+str(long)[0:7]+'&radius=2000')
                    print(response.content)
                    root = et.ElementTree(et.fromstring(response.content))         

                    if INIT:
                        Alldata = self.__parse_XML(root,df_cols)
                        INIT=False
                    else:
                        Alldata = Alldata.append(self.__parse_XML(root,df_cols)).drop_duplicates()

            Alldata.to_csv('locationdata.csv')

        else:
            Alldata=pd.read_csv('locationdata.csv')
        
        return Alldata  
    
    
    def __prepare_data(self):
        """Custom-defined function which takes the longitude and latitude of
        each bus stop and converts it to useful coordinates which can be used
        to plot on the map which is returned from another function. Additional 
        information is addd]ed to the bus stop data, including the directionality
        of the bus stop and the number of busses stopping there."""
        
        Alldata = self.busses
        leftCorner = 49.215351, -123.282268
        rightCorner = 49.291977, -123.023472

        Width = abs(leftCorner[1]-rightCorner[1])
        Height = abs(leftCorner[0]-rightCorner[0])

        w = 1520 / Width
        h = 700 / Height

        ycoords = np.array(rightCorner[0]-Alldata['Latitude'])*h 
        xcoords = np.array(leftCorner[1]-Alldata['Longitude'])*-w

        Alldata['Xcoords'] = xcoords
        Alldata['Ycoords'] = ycoords

        def trim(name):
            try:
                returned = name[:2]
                return returned
            except:
                return np.nan

        def length(name):
            try:
                length = str(len(name))
                conversion = {'3':1,'8':2,'13':3,'18':4,'23':5}
                truelength = conversion[length]
                return truelength
            except:
                return np.nan

        Alldata['Direction'] = [trim(x) for x in Alldata['Name']]
        Alldata['Num Stops'] = [length(x) for x in Alldata['Routes']]
        Coords = pd.DataFrame({'X':xcoords,'Y':ycoords},columns=['X','Y'])
        Coords = Coords[(Coords['X']>0) & (Coords['Y']>0) & (Coords['X']<1520) & (Coords['Y']<700)]
        index = Coords.index.tolist()
        Coords['# Busses'] = Alldata.iloc[index]['Num Stops']
        Coords['Direction'] = Alldata.iloc[index]['Direction']
        PermissibleDirections = ['NB','SB','EB','WB']
        Coords.loc[~Coords.Direction.isin(PermissibleDirections),'Direction'] = 'NA'
        Coords = Coords.fillna(0)
        
        return Coords
    
    def __mapquest_access(self):
        """This function uses the Mapquest API to GET an image of
        metro vancouver in the defined longitude and latitudinal
        coordinates with the specified pixel size. The function converts
        the return type from bytes to integer and cleans for plotting."""
        
        URL = 'https://www.mapquestapi.com/staticmap/v4/getmap?\
        key=JqeDWINXYaf3cRp7mwesQfPNt6GRzWaK&bestfit=49.291977,\
        -123.282268,49.215351,-123.023472&size=1520,700'
        
        image = requests.get(URL)
        image_bytes = img.content
        decoded = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), -1)
        plotimg = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
        plotimg = cv2.GaussianBlur(plotimg,(1,1),0)
        
        return plotimg
    
    def __plot(self):
        """This function plots both the image of metro Vancouver and 
        every stop in the region, with color coding for the stop 
        direction and the number of busses that stop there."""
        
        fig, ax = plt.subplots(figsize=(10,5),dpi=300)
        ax.imshow(self.plottedImage,alpha=0.7)
        fig = sns.scatterplot(x='X',y='Y',size='# Busses',hue='Direction',data=Coords,linewidth=0,alpha=0.5,sizes=(10, 50),palette=sns.color_palette("cubehelix", 5))
        plt.setp(fig.get_legend().get_texts(), fontsize='6',alpha=0.5)
        plt.axis('off')
        plt.savefig("test.png", bbox_inches='tight')
        
    

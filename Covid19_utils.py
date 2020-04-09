# Import des librairies
import pandas as pd
import json
import plotly.express as px
import plotly.offline
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets
import numpy as np
from ipywidgets import interact

# Chargement des données
def charge(local):
    # Source : # Source : https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/

    # Les méta données
    df_meta = pd.read_csv(local+'/Data/metadonnees-donnees-hospitalieres-covid19.csv', sep=';')
    df_type_data = pd.DataFrame({'colonne': ['hosp','rea','rad','dc'], 
                                'type_data': ['Nb actuellement hospitalisés',
                                            'Nb actuellement en réanimation',
                                            'Nb cumulé de retours à domicile',
                                            "Nb cumulé de décés à l'hôpital"]})
    dict_labels = {'legend':'Région - Département', 'nom_region':'Région', 'nom_departement': 'Département',
                'date':'Date', 'hosp':'Nb actuellement hospitalisés','rea':'Nb actuellement en réanimation',
                'rad':'Nb cumulé de retours à domicile','dc':"Nb cumulé de décés à l'hôpital"}
    # Les données
    df = pd.read_csv(local+'/Data/data.csv', sep=';')
    df = df[df.sexe == 0] # On ne considère que le niveau glov=bal

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://www.data.gouv.fr/fr/datasets/r/1c31f420-829e-489e-a19d-36cf3ef57e4a
    # Les données départements
    df_dept = pd.read_csv(local+'/Data/departements-france.csv')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://github.com/gregoiredavid/france-geojson/blob/master/departements.geojson
    with open(local+'/Data/dept.json') as jsonfile:
        geo = json.load(jsonfile)

    # Incorporation des infos départements au dataframe de données
    df = pd.merge(df, df_dept, left_on='dep', right_on='code_departement', how='left')
    df['infos'] = df['dep'] + " " + df['nom_departement'] + " (" + df['nom_region'] + ")"
    df['legend'] = df['nom_region'] + " - " + df['nom_departement']
    df['date'] = pd.to_datetime(df['jour'], format='%Y-%m-%d')
    df.dropna(inplace=True)

    # Séparation Paris / hors Paris
    df_hors_paris = df[~df['dep'].isin(['75', '92', '94', '93'])]
    df_paris = df[df['dep'].isin(['75', '92', '94', '93'])]

    # Aggrégation niveau régions
    df_agg_reg = df[['nom_region','date','hosp','rea','rad','dc']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    #regions = list(df_agg_reg['nom_region'].unique())

    return df_type_data, df_agg_reg, df, df_hors_paris, df_paris, dict_labels, geo


def plot_courbes_regions(df_type_data, Donnée, df_agg_reg, dict_labels, local):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    fig = px.line(df_agg_reg, x="date", y=colonne, color="nom_region", labels=(dict_labels),
                  hover_name="nom_region", 
                  title='COVID 19 - Evolution par région',
                  category_orders=({'nom_region': list(np.sort(df_agg_reg['nom_region'].unique()))}))
    fig.update_layout(title_x = 0.5)
    fig.update_yaxes(title_text=Donnée)
    fig.show()
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_par_region.html', auto_open=False)




def plot_courbes_departements(df_type_data, Donnée, df, dict_labels, local):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    fig = px.line(df, x="date", y=colonne, color="legend", facet_col='nom_region', facet_col_wrap=3,
                  labels=(dict_labels), hover_name="nom_departement", 
                  title="COVID 19 - Evolution par région départements",
                  width=1500, height=1500, 
                  category_orders=({'nom_region': list(np.sort(df['nom_region'].unique())),
                                    'legend': list(np.sort(df['legend'].unique()))}))             
    fig.update_layout(title_x = 0.5, showlegend=True)
    fig.update_yaxes(title_text=Donnée)
    fig.update_xaxes(showticklabels=True)
    fig.update_yaxes(matches=None)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

    fig['layout']['yaxis2']['title']['text']=''
    fig['layout']['yaxis3']['title']['text']=''
    fig['layout']['yaxis5']['title']['text']=''
    fig['layout']['yaxis6']['title']['text']=''
    fig['layout']['yaxis8']['title']['text']=''
    fig['layout']['yaxis9']['title']['text']=''
    fig['layout']['yaxis11']['title']['text']=''
    fig['layout']['yaxis12']['title']['text']=''
    fig['layout']['yaxis14']['title']['text']=''
    fig['layout']['yaxis15']['title']['text']=''
    fig['layout']['yaxis17']['title']['text']=''
    fig['layout']['yaxis18']['title']['text']=''


    fig.show()
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_par_region_dept.html', auto_open=False)



def plot_carte(df_type_data, Donnée, Zone, df_hors_paris, df_paris, geo, local):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    if Zone == 'Hors Paris':
        df_plot = df_hors_paris
        lib_zone = "hors région parisienne"
    else:
        df_plot = df_paris
        lib_zone = "en région parisienne"
        
    min = df_plot[colonne].min()
    max = df_plot[colonne].max()

    fig = px.choropleth(df_plot,
                        geojson=geo,
                        locations="dep", 
                        featureidkey="properties.code",
                        color=colonne,
                        animation_frame="jour",
                        hover_name="infos",
                        color_continuous_scale=px.colors.sequential.RdBu_r,
                        range_color=[min, max]
                       )

    fig.update_geos(fitbounds="locations", visible=False)
    #fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_layout(
   #     title_text = "COVID 19 - Evolution "+lib_zone+" - "+Donnée,
        title_x = 0.5,
        geo=dict(
            showframe = False,
            showcoastlines = False,
            projection_type = 'mercator'
        )
    )
    fig.show()
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_'+Zone.replace(' ','_')+'.html', auto_open=False)
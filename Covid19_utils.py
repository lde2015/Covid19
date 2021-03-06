import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.offline
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests
import io


#----------------------------------------------------------------------------------------------------------------------------
# Chargement des meta données
def charge_meta(local, nb_jours, ratio=10000):
    # Source : # Source : https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/

    # Les méta données
    lib_ratio = s='{:,}'.format(ratio).replace(',', '.')
    df_meta = pd.read_csv(local+'/Data/metadonnees-donnees-hospitalieres-covid19.csv', sep=';')
    df_type_data = pd.DataFrame({#'colonne': ['hosp','rea','rad','dc'], 
                                 'colonne': ['hosp','rea','dc'], 
                                'type_data': ['Nb actuellement hospitalisés',
                                            'Nb actuellement en réanimation',
                                          #  'Nb cumulé de retours à domicile',
                                            "Nb cumulé de décés à l'hôpital"]})
    dict_labels = {'legend':'Région - Département', 'nom_region':'Région', 'nom_departement': 'Département',
                'date':'Date', 'hosp':'Nb actuellement hospitalisés','rea':'Nb actuellement en réanimation',
                'rad':'Nb cumulé de retours à domicile','dc':"Nb cumulé de décés à l'hôpital",
                'hosp_ratio':"Ratio /"+lib_ratio+" hospitalisés", 'rea_ratio':"Ratio /"+lib_ratio+" en réanimation",
                'dc_ratio':"Ratio /"+lib_ratio+" décédés"}

    # Les nouveaux cas depuis 15 jours
    url = "https://www.data.gouv.fr/fr/datasets/r/6fadff46-9efd-4c53-942a-54aca783c30c"
    content = requests.get(url).content
    df_new = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=';')
    df_new['date'] = pd.to_datetime(df_new['jour'], format='%Y-%m-%d')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://www.data.gouv.fr/fr/datasets/r/1c31f420-829e-489e-a19d-36cf3ef57e4a
    # Les données départements
    df_dept = pd.read_csv(local+'/Data/departements-france.csv')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://www.insee.fr/fr/statistiques/1893198
    # La population, par département
    df_pop_dept = pd.read_csv(local+'/Data/population_dept.csv', sep=';')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://github.com/gregoiredavid/france-geojson/blob/master/departements.geojson
    with open(local+'/Data/dept.json') as jsonfile:
        geo = json.load(jsonfile)

    # Incorporation des infos départements au dataframe de données
    df_new = pd.merge(df_new, df_dept, left_on='dep', right_on='code_departement', how='left')
    df_new['infos_dept'] = df_new['code_departement'] + " " + df_new['nom_departement']

    df_new_agg_reg = df_new[['nom_region','date','incid_hosp','incid_rea','incid_dc']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    date_deb = df_new_agg_reg['date'].max() - timedelta(days=nb_jours)
    df_new = df_new[df_new.date >= date_deb]
    df_new_agg_reg = df_new_agg_reg[df_new_agg_reg.date >= date_deb]

    return df_type_data, df_new, df_new_agg_reg, dict_labels, geo, df_dept, df_pop_dept

#----------------------------------------------------------------------------------------------------------------------------
# Chargement des données
def charge_data(date_deb, df_dept, df_pop_dept, ratio=10000):
    dte_deb = pd.to_datetime(date_deb, format='%d/%m/%Y')
    
    # Les données
    url = "https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7"
    content = requests.get(url).content
    df = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=';')
    df = df[df.sexe == 0] # On ne considère que le niveau global

    df.dropna(inplace=True)
    df['test'] = df['jour'].apply(lambda x: np.where(x[:4] == '2020', True, False))
    df1 = df[df.test]
    df2 = df[~df.test]
    df1['date'] = pd.to_datetime(df1['jour'], format='%Y-%m-%d')
    df2['date'] = pd.to_datetime(df2['jour'], format='%d/%m/%Y')
    df = pd.concat([df1, df2]).sort_index()
    df = df[df.date >= dte_deb]

    # Incorporation des infos départements au dataframe de données
    df = pd.merge(df, df_dept, left_on='dep', right_on='code_departement', how='left')
    df = pd.merge(df, df_pop_dept[['dept','population']], left_on='dep', right_on='dept', how='left')
    df.drop(columns=['dep','sexe','dept'], axis=1, inplace=True)
    df['infos'] = df['code_departement'] + " " + df['nom_departement'] + " (" + df['nom_region'] + ")"
    df['legend'] = df['nom_region'] + " - " + df['nom_departement']
    
    df.dropna(inplace=True)
    df['hosp_ratio'] = df.apply(lambda x: np.round(x['hosp']*ratio/x['population'], 2), axis=1)
    df['rea_ratio'] = df.apply(lambda x: np.round(x['rea']*ratio/x['population'], 2), axis=1)
    df['rad_ratio'] = df.apply(lambda x: np.round(x['rad']*ratio/x['population'], 2), axis=1)
    df['dc_ratio'] = df.apply(lambda x: np.round(x['dc']*ratio/x['population'], 2), axis=1)

    # Séparation Paris / hors Paris
    df_hors_paris = df[df['nom_region'] != "Ile-de-France"]
    df_paris = df[df['nom_region'] == "Ile-de-France"]

    # Aggrégation niveau régions
    df_agg_reg = df[['nom_region','date','hosp','rea','rad','dc','population']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    #regions = list(df_agg_reg['nom_region'].unique())

    df_agg_reg['hosp_ratio'] = df_agg_reg.apply(lambda x: np.round(x['hosp']*ratio/x['population'], 2), axis=1)
    df_agg_reg['rea_ratio'] = df_agg_reg.apply(lambda x: np.round(x['rea']*ratio/x['population'], 2), axis=1)
    df_agg_reg['rad_ratio'] = df_agg_reg.apply(lambda x: np.round(x['rad']*ratio/x['population'], 2), axis=1)
    df_agg_reg['dc_ratio'] = df_agg_reg.apply(lambda x: np.round(x['dc']*ratio/x['population'], 2), axis=1)

    return df_agg_reg, df, df_hors_paris, df_paris

#----------------------------------------------------------------------------------------------------------------------------
# Chargement des meta données et des données
def charge(local, nb_jours, date_deb, ratio=10000):
    # Source : # Source : https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/

    # Les méta données
    lib_ratio = s='{:,}'.format(ratio).replace(',', '.')
    df_meta = pd.read_csv(local+'/Data/metadonnees-donnees-hospitalieres-covid19.csv', sep=';')
    df_type_data = pd.DataFrame({#'colonne': ['hosp','rea','rad','dc'], 
                                 'colonne': ['hosp','rea','dc'], 
                                'type_data': ['Nb actuellement hospitalisés',
                                            'Nb actuellement en réanimation',
                                            #'Nb cumulé de retours à domicile',
                                            "Nb cumulé de décés à l'hôpital"]})
    dict_labels = {'legend':'Région - Département', 'nom_region':'Région', 'nom_departement': 'Département',
                'date':'Date', 'hosp':'Nb actuellement hospitalisés','rea':'Nb actuellement en réanimation',
                'rad':'Nb cumulé de retours à domicile','dc':"Nb cumulé de décés à l'hôpital",
                'hosp_ratio':"Ratio /"+lib_ratio+" hospitalisés", 'rea_ratio':"Ratio /"+lib_ratio+" en réanimation",
                'dc_ratio':"Ratio /"+lib_ratio+" décédés"}
    # Les données
    url = "https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7"
    content = requests.get(url).content
    df = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=';')
    df = df[df.sexe == 0] # On ne considère que le niveau global

    dt_deb = pd.to_datetime(date_deb, format='%d/%m/%Y')
    df.dropna(inplace=True)
    df['test'] = df['jour'].apply(lambda x: np.where(x[:4] == '2020', True, False))
    df1 = df[df.test]
    df2 = df[~df.test]
    df1['date'] = pd.to_datetime(df1['jour'], format='%Y-%m-%d')
    df2['date'] = pd.to_datetime(df2['jour'], format='%d/%m/%Y')
    df = pd.concat([df1, df2]).sort_index()
    df = df[df.date >= dt_deb]

    # Les nouveaux cas depuis 15 jours
    url = "https://www.data.gouv.fr/fr/datasets/r/6fadff46-9efd-4c53-942a-54aca783c30c"
    content = requests.get(url).content
    df_new = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=';')
    df_new['date'] = pd.to_datetime(df_new['jour'], format='%Y-%m-%d')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://www.data.gouv.fr/fr/datasets/r/1c31f420-829e-489e-a19d-36cf3ef57e4a
    # Les données départements
    df_dept = pd.read_csv(local+'/Data/departements-france.csv')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://www.insee.fr/fr/statistiques/1893198
    # La population, par département
    df_pop_dept = pd.read_csv(local+'/Data/population_dept.csv', sep=';')

    #-------------------------------------------------------------------------------------------------------------------
    # Source : https://github.com/gregoiredavid/france-geojson/blob/master/departements.geojson
    with open(local+'/Data/dept.json') as jsonfile:
        geo = json.load(jsonfile)

    # Incorporation des infos départements au dataframe de données
    df = pd.merge(df, df_dept, left_on='dep', right_on='code_departement', how='left')
    df = pd.merge(df, df_pop_dept[['dept','population']], left_on='dep', right_on='dept', how='left')
    df.drop(columns=['dep','sexe','dept'], axis=1, inplace=True)
    df['infos'] = df['code_departement'] + " " + df['nom_departement'] + " (" + df['nom_region'] + ")"
    df['legend'] = df['nom_region'] + " - " + df['nom_departement']
    
    df.dropna(inplace=True)
    df['hosp_ratio'] = df.apply(lambda x: np.round(x['hosp']*ratio/x['population'], 2), axis=1)
    df['rea_ratio'] = df.apply(lambda x: np.round(x['rea']*ratio/x['population'], 2), axis=1)
    df['rad_ratio'] = df.apply(lambda x: np.round(x['rad']*ratio/x['population'], 2), axis=1)
    df['dc_ratio'] = df.apply(lambda x: np.round(x['dc']*ratio/x['population'], 2), axis=1)

    df_new = pd.merge(df_new, df_dept, left_on='dep', right_on='code_departement', how='left')
    df_new['infos_dept'] = df_new['code_departement'] + " " + df_new['nom_departement']

    # Séparation Paris / hors Paris
    df_hors_paris = df[df['nom_region'] != "Ile-de-France"]
    df_paris = df[df['nom_region'] == "Ile-de-France"]

    # Aggrégation niveau régions
    df_agg_reg = df[['nom_region','date','hosp','rea','rad','dc','population']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    #regions = list(df_agg_reg['nom_region'].unique())

    df_new_agg_reg = df_new[['nom_region','date','incid_hosp','incid_rea','incid_dc']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    date_deb = df_new_agg_reg['date'].max() - timedelta(days=nb_jours)
    df_new = df_new[df_new.date >= date_deb]
    df_new_agg_reg = df_new_agg_reg[df_new_agg_reg.date >= date_deb]

    df_agg_reg['hosp_ratio'] = df_agg_reg.apply(lambda x: np.round(x['hosp']*ratio/x['population'], 2), axis=1)
    df_agg_reg['rea_ratio'] = df_agg_reg.apply(lambda x: np.round(x['rea']*ratio/x['population'], 2), axis=1)
    df_agg_reg['rad_ratio'] = df_agg_reg.apply(lambda x: np.round(x['rad']*ratio/x['population'], 2), axis=1)
    df_agg_reg['dc_ratio'] = df_agg_reg.apply(lambda x: np.round(x['dc']*ratio/x['population'], 2), axis=1)

    return df_type_data, df_agg_reg, df, df_hors_paris, df_paris, df_new, df_new_agg_reg, dict_labels, geo

#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_regions(df_type_data, Donnée, df_agg_reg, dict_labels, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    fig = px.line(df_agg_reg, x="date", y=colonne, color="nom_region", labels=(dict_labels),
                  hover_name="nom_region", width=1200, height=600,
                  title='COVID-19 - Evolution par région - '+Donnée,
                  category_orders=({'nom_region': list(np.sort(df_agg_reg['nom_region'].unique()))}))
    fig.update_layout(title_x = 0.5)
    fig.update_yaxes(title_text=Donnée)

    if show == 'O':
        fig.show()

    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_par_region.html', auto_open=False)
    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_regions_ratio(df_type_data, Donnée, df_agg_reg, dict_labels, local, ratio=10000, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0] + "_ratio"
    lib_ratio = s='{:,}'.format(ratio).replace(',', '.')
    fig = px.line(df_agg_reg, x="date", y=colonne, color="nom_region", labels=(dict_labels),
                  hover_name="nom_region", width=1200, height=600,
                  title='COVID-19 - Evolution par région - '+Donnée+ '<br> - ratio pour '+lib_ratio+' habitants -</br>',
                  category_orders=({'nom_region': list(np.sort(df_agg_reg['nom_region'].unique()))}))
    fig.update_layout(title_x = 0.5)
    fig.update_yaxes(title_text=Donnée + " pour " + lib_ratio)

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_ratio_par_region.html', auto_open=False)
    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_departements(df_type_data, Donnée, df_plot, reg, dict_labels, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]    
    fig = px.line(df_plot, x="date", y=colonne, color="nom_departement",  
                      labels=(dict_labels), hover_name="nom_departement", 
                      title="COVID-19 - Evolution pour la région " + reg + "<br> - "+ Donnée + " - </br>",
                      width=1200, height=600, 
                      category_orders=({'nom_departement': list(np.sort(df_plot['nom_departement'].unique()))})
                 )             
    fig.update_layout(title_x = 0.5, showlegend=True,
                          legend=dict(font=dict(size=10)),
                          margin=dict(b=0),
                     )
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text=Donnée)
    fig.update_xaxes(showticklabels=True)
    fig.update_yaxes(matches=None)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
            
    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_'+reg+'.html', auto_open=False)

    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_departements_grid(df_type_data, Donnée, df, dict_labels, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    fig = px.line(df, x="date", y=colonne, color="legend", facet_col='nom_region', facet_col_wrap=3,
                  labels=(dict_labels), hover_name="nom_departement", 
                  title="COVID 19 - Evolution par région départements - "+Donnée,
                  width=1500, height=1500, 
                  category_orders=({'nom_region': list(np.sort(df['nom_region'].unique())),
                                    'legend': list(np.sort(df['legend'].unique()))}))             
    fig.update_layout(title_x = 0.5, showlegend=True, legend=dict(font=dict(size=10)))
    fig.update_yaxes(title_text=Donnée)
    fig.update_xaxes(showticklabels=True)
    fig.update_yaxes(matches=None)
    fig.update_yaxes(showticklabels=True, col=2)
    fig.update_yaxes(showticklabels=True, col=3)
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

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_par_region_dept.html', auto_open=False)

    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_departements_ratio(df_type_data, Donnée, df_plot, reg, dict_labels, local, ratio=10000, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0] + "_ratio"
    lib_ratio = s='{:,}'.format(ratio).replace(',', '.')

    fig = px.line(df_plot, x="date", y=colonne, color="nom_departement",  
                      labels=(dict_labels), hover_name="nom_departement", 
                      title="COVID-19 - Evolution pour la région " + reg + "<br>- "+ Donnée+' : ratio pour '+lib_ratio+' habitants -</br> ',
                      width=1200, height=600, 
                      category_orders=({'nom_departement': list(np.sort(df_plot['nom_departement'].unique()))})
                 )             
    fig.update_layout(title_x = 0.5, showlegend=True,
                          legend=dict(font=dict(size=10)),
                          margin=dict(b=0),
                     )
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text=Donnée)
    fig.update_xaxes(showticklabels=True)
    fig.update_yaxes(matches=None)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_ratio_'+reg+'.html', auto_open=False)

    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_departements_ratio_grid(df_type_data, Donnée, df, dict_labels, local, ratio=10000, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0] + "_ratio"
    lib_ratio = s='{:,}'.format(ratio).replace(',', '.')
    fig = px.line(df, x="date", y=colonne, color="legend", facet_col='nom_region', facet_col_wrap=3,
                  labels=(dict_labels), hover_name="nom_departement", 
                  title="COVID 19 - Evolution par région départements - "+Donnée+' : ratio pour '+lib_ratio+' habitants',
                  width=1500, height=1500, 
                  category_orders=({'nom_region': list(np.sort(df['nom_region'].unique())),
                                    'legend': list(np.sort(df['legend'].unique()))}))             
    fig.update_layout(title_x = 0.5, showlegend=True, legend=dict(font=dict(size=10)))
    fig.update_yaxes(title_text=Donnée)
    fig.update_xaxes(showticklabels=True)
    fig.update_yaxes(matches=None)
    fig.update_yaxes(showticklabels=True, col=2)
    fig.update_yaxes(showticklabels=True, col=3)
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

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_ratio_par_region_dept.html', auto_open=False)

    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_carte(df_type_data, dte_deb, Donnée, Zone, df_hors_paris, df_paris, geo, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    
    if Zone == 'Hors Paris':
        df_plot = df_hors_paris
        lib_zone = "hors région Ile-de-France"
    elif Zone == 'Paris':
        df_plot = df_paris
        lib_zone = "en région Ile-de-France"
    else:
        df_plot = pd.concat([df_hors_paris, df_paris], ignore_index=True)
        lib_zone = 'en France'

    df_plot = df_plot[df_plot.date >= dte_deb][['jour','hosp','rea','dc', \
                                                'hosp_ratio','rea_ratio','dc_ratio', \
                                                'date','code_departement','infos']]
    min = df_plot[colonne].min()
    max = df_plot[colonne].max()

    fig = px.choropleth(df_plot,
                        geojson=geo,
                        locations="code_departement", 
                        featureidkey="properties.code",
                        color=colonne,
                        animation_frame="jour",
                        hover_name="infos",
                        color_continuous_scale=px.colors.sequential.RdBu_r,
                        range_color=[min, max],
                        labels={'hosp':'Nb personnes', 'rea':'Nb personnes', 'rad':'Nb personnes',
                                'dc':'Nb personnes'}
                       )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title_text = "COVID-19 - Evolution sur les 15 derniers jours "+lib_zone+"<br>- "+Donnée + " -</br>",
        title_x = 0.5, 
        geo=dict(
            showframe = False,
            showcoastlines = False,
            projection_type = 'mercator'),
        width=700,
        height=600,
        margin=dict(
            l= 0,
            r= 0,
            b= 0,
            #t= 0,
            pad= 4)
    )
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1000

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_carte_'+Zone.replace(' ','_')+'.html', auto_open=False)

    return fig, colonne

#----------------------------------------------------------------------------------------------------------------------------
def plot_carte_ratio(df_type_data, dte_deb, Donnée, Zone, df_hors_paris, df_paris, geo, local, ratio=10000, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0] + "_ratio"
    lib_ratio = s='{:,}'.format(ratio).replace(',', '.')
    
    if Zone == 'Hors Paris':
        df_plot = df_hors_paris
        lib_zone = "hors région Ile-de-France"
    elif Zone == 'Paris':
        df_plot = df_paris
        lib_zone = "en région Ile-de-France"
    else:
        df_plot = pd.concat([df_hors_paris, df_paris], ignore_index=True)
        lib_zone = 'en France'

    df_plot = df_plot[df_plot.date >= dte_deb][['jour','hosp','rea','dc', \
                                                'hosp_ratio','rea_ratio','dc_ratio', \
                                                'date','code_departement','infos']]
    min = df_plot[colonne].min()
    max = df_plot[colonne].max()

    fig = px.choropleth(df_plot,
                        geojson=geo,
                        locations="code_departement", 
                        featureidkey="properties.code",
                        color=colonne,
                        animation_frame="jour",
                        hover_name="infos",
                        color_continuous_scale=px.colors.sequential.RdBu_r,
                        range_color=[min, max],
                        labels={'hosp':'Nb personnes', 'rea':'Nb personnes', 'rad':'Nb personnes',
                                'dc':'Nb personnes'}
                       )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title_text = "COVID-19 - Evolution sur les 15 derniers jours "+lib_zone+"<br>- "+Donnée+' : ratio pour '+lib_ratio+' habitants -</br> ',
        title_x = 0.5, 
        geo=dict(
            showframe = False,
            showcoastlines = False,
            projection_type = 'mercator'),
        width=700,
        height=600,
        margin=dict(
            l= 0,
            r= 0,
            b= 0,
            #t= 0,
            pad= 4)
    )
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1000

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_ratio_carte_'+Zone.replace(' ','_')+'.html', auto_open=False)

    return fig, colonne
#----------------------------------------------------------------------------------------------------------------------------
def plot_heatmap_regions(df_new_agg_reg, local, Zone, show='O'):
    if Zone == 'Tout':
        df_plot = df_new_agg_reg.copy()
        titre = 'COVID-19 - Evolution des nouveaux cas par région sur les 15 derniers jours'
    if Zone == 'Hors Paris':
        df_plot = df_new_agg_reg[df_new_agg_reg['nom_region'] != "Ile-de-France"]
        titre = 'COVID-19 - Evolution des nouveaux cas par région sur les 15 derniers jours - Hors région Ile-de-France'
    if Zone == 'Paris':
        df_plot = df_new_agg_reg[df_new_agg_reg['nom_region'] == "Ile-de-France"]
        titre = 'COVID-19 - Evolution des nouveaux cas en Ile-de-France sur les 15 derniers jours'

    fig = make_subplots(rows=1, cols=6,
                        subplot_titles=("Nb quotidien de personnes : Hospitalisées", \
                                        "                               Admises en réanimation", \
                                        "               Décédées"),
                        specs=[[{}, None, {}, None, {}, None]],
                        shared_yaxes=True)

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_hosp'],
        x=df_plot['date'],
        y=df_plot['nom_region'],
        name="Hosp. +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.27, title='Nb pers.', thickness=15)), row=1, col=1
    )

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_rea'],
        x=df_plot['date'],
        y=df_plot['nom_region'],
        name="Réa. +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.62, title='Nb pers.', thickness=15)), row=1, col=3
    )

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_dc'],
        x=df_plot['date'],
        y=df_plot['nom_region'],
        name="Décès +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.97, title='Nb pers.', thickness=15)), row=1, col=5
    )
    fig.update_layout(title_text=titre, title_x=0.5,
                    height=500, width=1200, margin=dict(l=0,r=0,b=50),#t=25),
                    xaxis=dict(
            domain=[0, 0.27]
        ),
        xaxis2=dict(
            domain=[0.35, 0.62]
        ),
        xaxis3=dict(
            domain=[0.7, 0.97]
        ))

    fig['layout']['yaxis']['autorange'] = "reversed"
    fig['layout']['yaxis2']['autorange'] = "reversed"
    fig['layout']['yaxis3']['autorange'] = "reversed"

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_Nouveaux_Cas_Régions_'+Zone.replace(' ','_')+'.html', auto_open=False)

    return fig
    
#----------------------------------------------------------------------------------------------------------------------------
def plot_heatmap_departements(df_new, local, Zone, show='O'):
    if Zone == 'Tout':
        df_plot = df_new.copy()
        titre = 'COVID-19 - Evolution des nouveaux cas par région et département sur les 15 derniers jours'
    if Zone == 'Hors Paris':
        df_plot = df_new[df_new['nom_region'] != "Ile-de-France"]
        titre = 'COVID-19 - Evolution des nouveaux cas par région et département sur les 15 derniers jours - Hors Ile-de-France'
    if Zone == 'Paris':
        df_plot = df_new[df_new['nom_region'] == "Ile-de-France"]    
        titre = 'COVID-19 - Evolution des nouveaux cas en Ile-de-France sur les 15 derniers jours'
    
    fig = make_subplots(rows=1, cols=6,
                        subplot_titles=("Nb quotidien de personnes : Hospitalisées", \
                                        "                               Admises en réanimation", \
                                        "               Décédées"),
                        specs=[[{}, None, {}, None, {}, None]],
                        shared_yaxes=True)

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_hosp'],
        x=df_plot['date'],
        y=[df_plot['nom_region'], df_plot['infos_dept']],
        name="Hosp. +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.27, title='Nb pers.', thickness=15)), row=1, col=1
    )

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_rea'],
        x=df_plot['date'],
        y=[df_plot['nom_region'], df_plot['infos_dept']],
        name="Réa. +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.62, title='Nb pers.', thickness=15)), row=1, col=3
    )

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_dc'],
        x=df_plot['date'],
        y=[df_plot['nom_region'], df_plot['infos_dept']],
        name="Décès +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.97, title='Nb pers.', thickness=15)), row=1, col=5
    )
    fig.update_layout(title_text=titre, title_x=0.5,
                    height=2200, width=1200, margin=dict(l=0,r=0,b=50),#t=25),
                    xaxis=dict(
            domain=[0, 0.27]
        ),
        xaxis2=dict(
            domain=[0.35, 0.62]
        ),
        xaxis3=dict(
            domain=[0.7, 0.97]
        ))

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_Nouveaux_Cas_Départements_'+Zone.replace(' ','_')+'.html', auto_open=False)

    return fig

#----------------------------------------------------------------------------------------------------------------------------
def plot_heatmap_1region(df_plot, reg, local, show='O'):
    titre = 'COVID-19 - Evolution des nouveaux cas sur les 15 derniers jours - région '+reg
    nb_depts = len(df_plot['code_departement'].unique())
    
    fig = make_subplots(rows=1, cols=6,
                        subplot_titles=("   Nb quotidien de personnes : Hospitalisées", \
                                        "                         Admises en réanimation", \
                                        "                Décédées"),
                        specs=[[{}, None, {}, None, {}, None]],
                        shared_yaxes=True)

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_hosp'],
        x=df_plot['date'],
        y=df_plot['nom_departement'],
        name="Hosp. +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.27, title='Nb pers.', thickness=15)), row=1, col=1
    )

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_rea'],
        x=df_plot['date'],
        y=df_plot['nom_departement'],
        name="Réa. +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.62, title='Nb pers.', thickness=15)), row=1, col=3
    )

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_dc'],
        x=df_plot['date'],
        y=df_plot['nom_departement'],
        name="Décès +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.97, title='Nb pers.', thickness=15)), row=1, col=5
    )
    fig.update_layout(title_text=titre, title_x=0.5, 
                    height=500, width=1200, margin=dict(l=0,r=0,b=50),#t=25),
                    xaxis=dict(
            domain=[0, 0.27]
        ),
        xaxis2=dict(
            domain=[0.35, 0.62]
        ),
        xaxis3=dict(
            domain=[0.7, 0.97]
        ))

    fig['layout']['yaxis']['autorange'] = "reversed"
    fig['layout']['yaxis2']['autorange'] = "reversed"
    fig['layout']['yaxis3']['autorange'] = "reversed"

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_Nouveaux_Cas_Région_'+reg.replace(' ','_')+'.html', auto_open=False)

    return fig

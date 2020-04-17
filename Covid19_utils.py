# Import des librairies
import pandas as pd
import json
from datetime import timedelta
import plotly.express as px
import plotly.offline
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets
import numpy as np
from ipywidgets import interact

#----------------------------------------------------------------------------------------------------------------------------
# Chargement des données
def charge(local, nb_jours):
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

    # Les nouveaux cas depuis 15 jours
    df_new = pd.read_csv(local+'/Data/new.csv', sep=';')
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
    df['date'] = pd.to_datetime(df['jour'], format='%Y-%m-%d')
    df.dropna(inplace=True)

    df_new = pd.merge(df_new, df_dept, left_on='dep', right_on='code_departement', how='left')
    df_new['infos_dept'] = df_new['code_departement'] + " " + df_new['nom_departement']

    # Séparation Paris / hors Paris
    df_hors_paris = df[df['nom_region'] != "Île-de-France"]
    df_paris = df[df['nom_region'] == "Île-de-France"]

    # Aggrégation niveau régions
    df_agg_reg = df[['nom_region','date','hosp','rea','rad','dc','population']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    #regions = list(df_agg_reg['nom_region'].unique())

    df_new_agg_reg = df_new[['nom_region','date','incid_hosp','incid_rea','incid_dc']].groupby(['nom_region','date']).aggregate('sum').reset_index()
    date_deb = df_new_agg_reg['date'].max() - timedelta(days=nb_jours)
    df_new = df_new[df_new.date >= date_deb]
    df_new_agg_reg = df_new_agg_reg[df_new_agg_reg.date >= date_deb]

    df_agg_reg['hosp_pct'] = df_agg_reg.apply(lambda x: np.round(x['hosp']*100/x['population'], 2), axis=1)
    df_agg_reg['rea_pct'] = df_agg_reg.apply(lambda x: np.round(x['rea']*100/x['population'], 2), axis=1)
    df_agg_reg['rad_pct'] = df_agg_reg.apply(lambda x: np.round(x['rad']*100/x['population'], 2), axis=1)
    df_agg_reg['dc_pct'] = df_agg_reg.apply(lambda x: np.round(x['dc']*100/x['population'], 2), axis=1)

    return df_type_data, df_agg_reg, df, df_hors_paris, df_paris, df_new, df_new_agg_reg, dict_labels, geo


#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_regions(df_type_data, Donnée, df_agg_reg, dict_labels, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    fig = px.line(df_agg_reg, x="date", y=colonne, color="nom_region", labels=(dict_labels),
                  hover_name="nom_region", 
                  title='COVID 19 - Evolution par région - '+Donnée,
                  category_orders=({'nom_region': list(np.sort(df_agg_reg['nom_region'].unique()))}))
    fig.update_layout(title_x = 0.5)
    fig.update_yaxes(title_text=Donnée)

    if show == 'O':
        fig.show()

    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_par_region.html', auto_open=False)
    return fig, colonne


#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_regions_pct(df_type_data, Donnée, df_agg_reg, dict_labels, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0] + "_pct"
    fig = px.line(df_agg_reg, x="date", y=colonne, color="nom_region", labels=(dict_labels),
                  hover_name="nom_region", 
                  title='COVID 19 - Evolution par région - '+Donnée,
                  category_orders=({'nom_region': list(np.sort(df_agg_reg['nom_region'].unique()))}))
    fig.update_layout(title_x = 0.5)
    fig.update_yaxes(title_text=Donnée)

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_pct_par_region.html', auto_open=False)
    return fig, colonne


#----------------------------------------------------------------------------------------------------------------------------
def plot_courbes_departements(df_type_data, Donnée, df, dict_labels, local, show='O'):
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
def plot_carte(df_type_data, Donnée, Zone, df_hors_paris, df_paris, geo, local, show='O'):
    colonne = df_type_data[df_type_data.type_data == Donnée]['colonne'].reset_index(drop=True)[0]
    if Zone == 'Hors Paris':
        df_plot = df_hors_paris
        lib_zone = "hors région Île-de-France"
    else:
        df_plot = df_paris
        lib_zone = "en région Île-de-France"
        
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
        title_text = "COVID 19 - Evolution "+lib_zone+" : "+Donnée,
        title_x = 0.5,
        geo=dict(
            showframe = False,
            showcoastlines = False,
            projection_type = 'mercator'),
        width=800,
        height=800,
        margin=dict(
            l= 0,
            r= 0,
            b= 0,
            #t= 0,
            pad= 2)
    )
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 2000

    if show == 'O':
        fig.show()
    
    if local != ".":
        fig.write_html(local+'/Output/Evol_'+colonne+'_'+Zone.replace(' ','_')+'.html', auto_open=False)

    return fig, colonne


#----------------------------------------------------------------------------------------------------------------------------
def plot_heatmap_regions(df_new_agg_reg, local, Zone, show='O'):
    if Zone == 'Tout':
        df_plot = df_new_agg_reg.copy()
        titre = 'COVID-19 - Evolution des nouveaux cas par région sur les 15 derniers jours'
    if Zone == 'Hors Paris':
        df_plot = df_new_agg_reg[df_new_agg_reg['nom_region'] != "Île-de-France"]
        titre = 'COVID-19 - Evolution des nouveaux cas par région sur les 15 derniers jours - Hors région Île-de-France'
    if Zone == 'Paris':
        df_plot = df_new_agg_reg[df_new_agg_reg['nom_region'] == "Île-de-France"]
        titre = 'COVID-19 - Evolution des nouveaux cas en Île-de-France sur les 15 derniers jours'

    fig = make_subplots(rows=1, cols=6,
                        subplot_titles=("Nb quotidien de personnes : Hospitalisées", \
                                        "                               Admises en réanimation", \
                                        "               Décédées"),
                        specs=[[{}, None, {}, None, {}, None]],
                        shared_yaxes=True)

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_rea'],
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
        z=df_plot['incid_rea'],
        x=df_plot['date'],
        y=df_plot['nom_region'],
        name="Décès +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.97, title='Nb pers.', thickness=15)), row=1, col=5
    )
    fig.update_layout(title_text=titre, title_x=0.5,
                    height=550, width=1500, margin=dict(l=0,r=0,b=50),#t=25),
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
        df_plot = df_new[df_new['nom_region'] != "Île-de-France"]
        titre = 'COVID-19 - Evolution des nouveaux cas par région et département sur les 15 derniers jours - Hors Île-de-France'
    if Zone == 'Paris':
        df_plot = df_new[df_new['nom_region'] == "Île-de-France"]    
        titre = 'COVID-19 - Evolution des nouveaux cas en Île-de-France sur les 15 derniers jours'
    
    fig = make_subplots(rows=1, cols=6,
                        subplot_titles=("Nb quotidien de personnes : Hospitalisées", \
                                        "                               Admises en réanimation", \
                                        "               Décédées"),
                        specs=[[{}, None, {}, None, {}, None]],
                        shared_yaxes=True)

    fig.add_trace(go.Heatmap(
        z=df_plot['incid_rea'],
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
        z=df_plot['incid_rea'],
        x=df_plot['date'],
        y=[df_plot['nom_region'], df_plot['infos_dept']],
        name="Décès +",
        colorscale='RdBu',
        reversescale=True,
        colorbar = dict(x=0.97, title='Nb pers.', thickness=15)), row=1, col=5
    )
    fig.update_layout(title_text=titre, title_x=0.5,
                    height=2200, width=1700, margin=dict(l=0,r=0,b=50),#t=25),
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

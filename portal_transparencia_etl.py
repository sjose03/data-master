import pandas as pd

import glob
import os
  
# merging the files
joined_files_cad_bacen = os.path.join("data", "*Cadastro_Servidores_BACEN.csv")
joined_files_rem_bacen = os.path.join("data", "*Remuneracao_Servidores_BACEN.csv")

# A list of all joined files is returned
joined_files_cad_bacen = glob.glob(joined_files_cad_bacen)
joined_files_rem_bacen = glob.glob(joined_files_rem_bacen)

dfs_cadastro_bacen = []
for path in joined_files_cad_bacen:
    date_path = path.split('/')[1].split('_')[0]
    df = pd.read_csv(path, sep=";",encoding='latin-1')
    df['data_carga'] = date_path
    dfs_cadastro_bacen.append(df)

dfs_remuneracao_bacen = []
for path in joined_files_rem_bacen:
    date_path = path.split('/')[1].split('_')[0]
    df = pd.read_csv(path, sep=";",encoding='latin-1')
    df['data_carga'] = date_path
    dfs_remuneracao_bacen.append(df)

df_cadastro_full_ = pd.concat(dfs_cadastro_bacen)

df_remuneracao_full_ = pd.concat(dfs_remuneracao_bacen)

df_remuneracao_full_.shape

columns_rem_cleanse = [x.replace(" ","_").replace("-","_").replace("/","_").replace("__","_").replace("(R$)","R").replace("(U$)","U").upper().replace("Ç","C")
 .replace("Ã","A").replace("Á","A").replace("Õ","O").replace("Ú","U").replace("Ó","O")
 .replace("É","E")
 for x in df_remuneracao_full_.columns]

columns_cad_cleanse = [x.replace(" ","_").replace("-","_").replace("/","_").replace("(R$)","R").replace("(U$)","U").upper().replace("Ç","C")
 .replace("Ã","A").replace("Á","A").replace("Õ","O").replace("Ú","U").replace("Ó","O")
 .replace("É","E")
 for x in df_cadastro_full_.columns]

df_cadastro_full_.columns = columns_cad_cleanse

df_remuneracao_full_.columns = columns_rem_cleanse

df_remuneracao_full_.shape

df_remuneracao_full_clean = df_remuneracao_full_.dropna()

df_cadastro_full_clean = df_cadastro_full_.dropna()

df_cadastro_select = df_cadastro_full_[['ID_SERVIDOR_PORTAL','SITUACAO_VINCULO','CODIGO_ATIVIDADE','NOME','UF_EXERCICIO','JORNADA_DE_TRABALHO','DATA_INGRESSO_CARGOFUNCAO','COD_TIPO_VINCULO','SIGLA_FUNCAO','NIVEL_FUNCAO','FUNCAO','ATIVIDADE','TIPO_VINCULO','DATA_CARGA']]

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import *

connectionString = "mongodb://root:12345678@mongo:27017/admin.transparencia_salario"

spark = (SparkSession.builder
   .master("local[3]")
   .appName("batch")
   .config("spark.submit.deployMode","client")
    .config("spark.hadoop.fs.defaultFS", "hdfs://hadoop-env:9090")\
    .config("spark.jars", "mysql-connector-java-8.0.29.jar")
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1")
    .config("spark.mongodb.read.connection.uri",connectionString)
    .config("spark.mongodb.write.connection.uri",connectionString)
   .getOrCreate())

spark

df_remuneracao_full_clean['ID_SERVIDOR_PORTAL'] =  df_remuneracao_full_clean['ID_SERVIDOR_PORTAL'].astype('string').str.slice(0,8).copy()

df_rem = spark.createDataFrame(df_remuneracao_full_clean)

# Dropa colunas inuteis
colunas_drop_rem = [x for x in df_rem.columns if '_U' in x]

df_rem = df_rem.drop(*colunas_drop_rem + ['ANO','MES','CPF'])

# ajusta o nome das colunas
for coluna in [x for x in df_rem.columns if ('__' in x) or ('(*)' in x)]:
    df_rem = df_rem.withColumnRenamed(coluna,coluna.replace("__","_").replace('(*)',''))

## Dropa colunas com todos os valores zerados
drop_columns = []
for coluna in [x[0] for x in df_rem.dtypes[5:-1]]:
    df_rem = df_rem.withColumn(coluna,F.regexp_replace(F.col(coluna),',','.').cast('double'))
    df_describe = df_rem.select(F.col(coluna)).describe()
    if df_describe.filter(F.col(coluna) == 0.0).count() >=2:
        drop_columns.append(coluna)
df_rem = df_rem.drop(*drop_columns)

df_rem.write.jdbc('jdbc:mysql://mysqlsrv:3306/mydb?useSSL=false','REMUNERACAO',mode='overwrite',
                     properties = {"user":"root", "password":"12345678","driver":"com.mysql.jdbc.Driver"} )

df_cad = spark.createDataFrame(df_cadastro_select)

df_funcao = df_cad.select(
 'SIGLA_FUNCAO',
 'NIVEL_FUNCAO',
 'FUNCAO')

df_funcao = df_funcao.withColumn('SIGLA_FUNCAO',F.when(F.col('SIGLA_FUNCAO') == '-1','NAN').otherwise(F.col('SIGLA_FUNCAO')))

df_vinculos =  df_cad.select(
 'COD_TIPO_VINCULO',
 'TIPO_VINCULO',
'SITUACAO_VINCULO'
)

df_atividades =  df_cad.select(
 'CODIGO_ATIVIDADE',
 'ATIVIDADE')

df_atividades = df_atividades.withColumn('CODIGO_ATIVIDADE',F.when(F.col('CODIGO_ATIVIDADE') == '-1','F000').otherwise(F.col('CODIGO_ATIVIDADE')))

fk_columns = df_atividades.columns[1:] + df_vinculos.columns[1:] + df_funcao.columns[1:]

except_columns = [x for x in df_cad.columns if x not in fk_columns]

df_cad_table =( df_cad
.withColumn('SIGLA_FUNCAO',F.when(F.col('SIGLA_FUNCAO') == '-1','NAN').otherwise(F.col('SIGLA_FUNCAO')))
.withColumn('CODIGO_ATIVIDADE',F.when(F.col('CODIGO_ATIVIDADE') == '-1','F000').otherwise(F.col('CODIGO_ATIVIDADE')))
).select(except_columns)

df_cad_table.write.jdbc('jdbc:mysql://mysqlsrv:3306/mydb?useSSL=false','CADASTRO',mode='overwrite',
                     properties = {"user":"root", "password":"12345678","driver":"com.mysql.jdbc.Driver"} )

df_funcao.write.jdbc('jdbc:mysql://mysqlsrv:3306/mydb?useSSL=false','FUNCOES',mode='overwrite',
                     properties = {"user":"root", "password":"12345678","driver":"com.mysql.jdbc.Driver"} )

df_atividades.write.jdbc('jdbc:mysql://mysqlsrv:3306/mydb?useSSL=false','ATIVIDADES',mode='overwrite',
                     properties = {"user":"root", "password":"12345678","driver":"com.mysql.jdbc.Driver"} )

df_vinculos.write.jdbc('jdbc:mysql://mysqlsrv:3306/mydb?useSSL=false','VINCULOS',mode='overwrite',
                     properties = {"user":"root", "password":"12345678","driver":"com.mysql.jdbc.Driver"} )

df_join = df_rem.join(df_cad.filter('TIPO_VINCULO = "Função"'),['ID_SERVIDOR_PORTAL','DATA_CARGA'],how='left')

df_join_clean = df_join.filter('SITUACAO_VINCULO is not null')

df_join_clean = (
    df_join_clean.withColumn(
        'tempo_cargo',
        F.abs(F.round(F.year(F.to_date('DATA_INGRESSO_CARGOFUNCAO','dd/mm/yyyy'))-F.year((F.current_date())),0))
    )
)

df_mongo = df_join_clean.select('ID_SERVIDOR_PORTAL','tempo_cargo')

(    
    df_mongo.write.format("com.mongodb.spark.sql.DefaultSource")
        .mode('overwrite')
       .option("uri",connectionString)
       .option("database","admin")
       .option("collection","transparencia_salario")
    .save()
      )

df_mongo = df_join_clean.select('ID_SERVIDOR_PORTAL','tempo_cargo')
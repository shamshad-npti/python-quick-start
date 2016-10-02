from gcloud import bigquery
from oauth2client.service_account import ServiceAccountCredentials

credentials = ServiceAccountCredentials.from_json_keyfile_name('db-reporting-key.json')

client = bigquery.Client(credentials=credentials, project='dainik-bhaskar-1356')

# to get the list of dataset
datasets = client.list_datasets()

# to get a particular dataset
# here '34831806' is the name of the dataset
dataset = client.dataset('34831806')

# to list all tables in datasets
tables = [table for table in dataset.list_tables()]

print(tables[0][0].name)
# create a query (a simple python string)
query = '''
    SELECT 
      trafficSource.source AS source,
      COUNT(totals.visits) AS totals_sessions
    FROM 
      [dainik-bhaskar-1356:34831806.ga_sessions_20160814]
    GROUP BY
      source
    ORDER BY 
      totals_sessions DESC
    LIMIT 5
'''
# run query
query_result = client.run_sync_query(query)
query_result.run()

# to iterate over resulted rows of the query
for result in query_result.rows:
    print(result)

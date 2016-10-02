from gcloud import bigquery
from oauth2client.service_account import ServiceAccountCredentials

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    filename="db-reporting-key.json")

client = bigquery.Client(credentials=credentials,
    project='dainik-bhaskar-1356')

datasets, next_page_token = client.list_datasets() # API Call
print ("-- List of datasets --")
for dataset in datasets:
    print (dataset.name)

tables, next_page_token = datasets[0].list_tables()
table_name = []
while True:
    for table in tables:
        table_name.append(table.name)
    if next_page_token:
        tables, next_page_token = datasets[0].list_tables(page_token=next_page_token)
    else:
        break

print("-- List of tables in %s --" % datasets[0].name)
print('\n'.join(table_name[-10:]))

query = '''
    SELECT 
        IF(totals.newvisits IS NULL, 'Returning User', 'New User') AS USER_TYPE,
        DATE,
        COUNT(totals.visits) SESSIONS,
        AVG(totals.pageviews) AS PAGE_DEPTH
    FROM
        TABLE_DATE_RANGE([34831806.ga_sessions_], TIMESTAMP('2016-07-01'), TIMESTAMP('2016-07-07'))
    GROUP BY
        USER_TYPE, DATE
    ORDER BY DATE, USER_TYPE
'''
query_result = client.run_sync_query(query)
query_result.run()

# Print schema information of the returned result
print ("-- Query result --")
print (map(lambda x: (x.name, x.field_type), query_result.schema))
# print data in returned response
# Each row is represented by a tuple and entire result is just a python array of tuples
print ('\n'.join(map(str, query_result.rows)))


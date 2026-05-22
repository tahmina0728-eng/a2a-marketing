from google.cloud import storage
from google.cloud import bigquery
 
print("Testing GCS...")
client = storage.Client(project="dauntless-karma-497108-b0")
print("GCS connected:", client.project)
 
print("Testing BigQuery...")
bq = bigquery.Client(project="dauntless-karma-497108-b0")
tables = list(bq.list_tables("campaignos"))
print("BigQuery tables:", [t.table_id for t in tables])
 
print("")
print("All connections OK!")
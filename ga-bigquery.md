# Analysing GA Data in Bigquery
In this tutorial I would discuss how we can query GA data from bigquery and get some useful insights from the data. In the first part, I will show how we can get some very common GA metrics such as `Sessions`, `Page / Session`, `Users`, and `Pageviews` from BigQuery. In the second part, I would discuss how can we use bigquery to perform `hit level analysis`. In the last part, we focus on extended use of biguqery to combine GA data with backend ecommerce data to perform analysis.

### Outline
1. Understanding GA BigQuery export schema
2. Querying session level data
  1. Get sessions, pageviews metrics
  2. Get sessions, pageviews metrics grouped by some dimensions
3. Querying hit level data
  1. Using bigquery to segment users
  2. Understanding user behaviour using bigquery
4. Combine GA bigquery data with backend ecommerce data
  1. Performing Simple Join
  2. Understanding different type of join

## Understaing GA BigQuery Export Schema
#### Schema
Schema describes the structure of bigquery table. It defines each field and its datatype. Each bigquery table is bound to a schema. If data to be ingested doesn't conform to schema bigquery will give error.

#### Datasets
Dataset contains a collection of table. When GA is linked to a bigquery, name of the `dataset` is the same as id of the `profile` in GA. 

#### Tables
Table in bigquery is collection of schema bound rows and columns. Name of the tables which are exported to bigquery from GA starts with `ga_sessions_` followed by date string in the format of `yyyymmdd`.

#### Rows
Each row in table is equivalent to a GA session.

#### Some fields and conventions

| Field                 | Type        | Description                   |
|-----------------------|-------------|-------------------------------|
| fullVisitorId         | STRING      | A unique identifier for the user |
| totals.visits         | INTEGER     | `1` for session with interaction, `null` otherwise |
| totals.pageviews      | INTEGER     | Total number of pages visited during the session   |
| totals.newVisits      | INTEGER     | `1` if it is new visit, `null` for returning user  |
| totals.durationOnSite | INTEGER     | Number of seconds spend on the site                |
| trafficSource.source  | STRING      | Source of the traffic |
| trafficSource.medium  | STRING      | Medium of the traffic |
| hits.type             | STRING      | Type of the hits      |
| hits.page.*           | STRING      | Populated for each hit with type `PAGE` |

You can get complete list of fields with details here: 
[BigQuery Export Schema](https://support.google.com/analytics/answer/3437719?hl=en)

## Querying Session Level Data
### Get sessions, pageviews and other metrics metrics
The following query will return exact return for each of the metrics it is calculating. But when we run this query on a huge table it may by very slow.

```sql
SELECT
	COUNT(totals.visits) AS sessions,
	SUM(totals.pageviews) AS pageviews,
	AVG(totals.pageviews) AS page_per_session,
	EXACT_COUNT_DISTINCT(fullVisitorId) AS users,
	COUNT(totals.newVisits) AS new_visits,
FROM
	[xxxxxxxx.ga_sessions_20160801]
```
> Output:
Query complete (12.4s elapsed, 103 MB processed)

| sessions | pageviews | page_per_sessions | users  | new_visits |
|----------|-----------|-------------------|--------|------------|
| 2710348  | 11265869  | 4.16              | 1574936| 1000278    |

When we are dealing with huge number of session and we only want to get an approximation of unique visitors this query would be much faster. Notice that in the previous query I have used `EXACT_COUNT_DISTINCT` but in the following query `COUNT(DISTINCT field)` function is used

```sql
SELECT
	COUNT(totals.visits) AS sessions,
	SUM(totals.pageviews) AS pageviews,
	AVG(totals.pageviews) AS page_per_session,
	COUNT(DISTINCT fullVisitorId) AS users,
	COUNT(totals.newVisits) AS new_visits,
FROM
	[xxxxxxxx.ga_sessions_20160801]
```
> Output:
Query complete (2.6s elapsed, 103 MB processed)

| sessions | pageviews | page_per_sessions | users  | new_visits |
|----------|-----------|-------------------|--------|------------|
| 2710348  | 11265869  | 4.16              | 1709471| 1000278    |

### Get sessions, pageviews and other metrics grouped by some dimensions
If we need to query some metrics grouped by one or more dimension(s) the following query template could be helpful

```sql
SELECT
	{dimension1} AS dimension1,
	{dimension2} AS dimension2,
	{metric1} AS metric1,
	{metric2} AS metric2
FROM
	[{tables}]
GROUP BY
	dimension1,
	dimension2
ORDER BY
	metric1 DESC
```

For example if we want to query sessions, pageviews, and other metrics grouped by `traffic source` we can use following query. This query will output top five traffic source ordered by sessions.

```sql
SELECT
	trafficSource.source AS source,
	COUNT(totals.visits) AS sessions,
	SUM(totals.pageviews) AS pageviews,
	AVG(totals.pageviews) AS page_per_session,
	EXACT_COUNT_DISTINCT(fullVisitorId) AS users,
	COUNT(totals.newVisits) AS new_visits,
FROM
	[xxxxxxxx.ga_sessions_20160801]
GROUP BY 
	source
ORDER BY 
	sessions DESC
LIMIT
	5
```

> Output: Query complete (4.3s elapsed, 132 MB processed)

| source     | sessions | pageviews | page_per_session | users | new_visits |
|------------|----------|-----------|------------------|-------|------------|
|google      |    999707|    4256383|              4.26| 651349|      379714|
|facebook ads|	  453411|    1484718|              3.27| 287435|      137531|
|(direct)    |    271535|    1189766|              4.39| 200188|      167626|
|criteo      |    172485|	  932997|              5.42|  83928|        5211|
|masoffer    |    155265|	  380416|              2.45| 128133|       85593|

Following query is useful when we are accessing a huge table but we still want exact count of `fullVisitorId`, i.e. uniquer visitors. Notice that we have used `GROUP EACH BY` which is generally faster than just `GROUP BY` 

```sql
SELECT
	source,
	SUM(sessions) AS sessions,
	SUM(pageviews) AS pageviews,
	COUNT(fullVisitorsId) AS users,
	SUM(new_visits) AS new_visits
FROM (
	SELECT
		trafficSource.source AS source,
		fullVisitorId,
		COUNT(totals.visits) AS sessions,
		SUM(totals.pageviews) AS pageviews,
		COUNT(totals.newVisits) AS new_visits
	FROM
		[xxxxxxxx.ga_sessions_20160801]
	GROUP EACH BY
		source,
		fullVisitorId
) GROUP BY
	source
ORDER BY 
	sessions DESC
LIMIT 5
```
> Output: Query complete (3.7s elapsed, 132 MB processed)

| source     | sessions | pageviews | users | new_visits |
|------------|----------|-----------|-------|------------|
|google      |    999707|    4256383| 651349|      379714|
|facebook ads|	  453411|    1484718| 287435|      137531|
|(direct)    |    271535|    1189766| 200188|      167626|
|criteo      |    172485|	  932997|  83928|        5211|
|masoffer    |    155265|	  380416| 128133|       85593|


## Querying hit level data
### Using bigquery to segment user
We can use bigquery to segment users. For example you have an ecommerce site. You want to see the users who never visited a particular section of website and the users who visited that section. Further you want to analyze conversion rate for both type of user. 

Following query gives the list of fullVisitorId who never visited a particular section of your website. Let say that section is identified by `/christmas-deal/`

```sql
SELECT
	fullVisitorId
FROM
	[xxxxxxxxxxx.ga_sessions_20160801]
WHERE
	NOT REGEXP_MATCH(hits.page.pagePath, r'/cristmas\-deal/')
LIMIT 5
```
> Output:
Query complete (4.3s elapsed, 104 MB processed)

|   fullVisitorId    |
|--------------------|
| 2969779731265662935|
| 2969845384144150784|
| 2969846960397151490|
| 2969865561891340530|
| 2969881058140092410|

### Understanding user behaviour using bigquery
Suppose an ecommerce company has a blog site for different products and they want to know visitors who visit your site frequently. The company sells fitness product and it maintains a blog on fitness. It wants to know loyal readers or the readers who visit for at least 20 days in a month. This kind of query is not possible in GA but it can be done bigquery.

The following query 

```sql
-- This query is using standard sql instead
-- of bigquery legacy sql

WITH user_with_visit_by_date AS (
  SELECT 
    fullVisitorId,
    DATE
  FROM
    `xxxxxxxxx.ga_sessions_*`
  WHERE
    _TABLE_SUFFIX >= '20160701'
    AND _TABLE_SUFFIX <= '20160731'
    AND totals.visits IS NOT NULL
  GROUP BY
    fullVisitorId,
    date
), visit_count_per_month AS (
  SELECT
    fullVisitorId,
    COUNT(1) AS visit_count
  FROM 
    user_with_visit_by_date
  GROUP BY
    fullVisitorId
) 
SELECT
  fullVisitorId,
  visit_count
FROM
  visit_count_per_month
WHERE
  visit_count >= 20 
LIMIT 5
```

> Output: Query complete (9.6s elapsed, 324 MB processed)

| fullVisitorId	      |visit_count|
|---------------------|-----------|
| 2239253515594958753 |         20|
| 441756856944002620  |         26|
| 6275416274293383463 |         24|
| 489814981189865265  |         21|
| 219806051024923901  |         25|

## Combine GA bigquery data with backend ecommerce data
### Performing Simple Join
### Understanding different type of join

#### Inner Join 
Equivalent to interection in set theory

```sql
SELECT
	a.fields,
	b.fields
FROM
	table1 AS a
INNER JOIN 
	table2 AS b
ON
	a.id = b.id
```

#### Left Join 
Keep All from left table. If some rows in left table don't have matching rows in right table all fields of right table for those rows are null
```sql
SELECT
	a.fields,
	b.fields
FROM
	leftTable as a
LEFT JOIN
	rightTable as b
ON
	a.id = b.id
```
#### Right Join
Keep all from right table and unmatched right table rows have null values for all left table fields
```sql
SELECT
	a.fields,
	b.fields
FROM
	leftTable as a
RIGHT JOIN
	rightTable as b
ON
	a.id = b.id
```
#### Difference (Left - Right)
```sql
SELECT
	a.fields,
	b.fields
FROM
	leftTable as a
RIGHT JOIN
	rightTable as b
ON
	a.id = b.id
WHERE
	b.id IS NULL
```

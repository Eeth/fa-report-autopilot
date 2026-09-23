#Day 1 Findings

Set up docker
Set up PostgresSQL within docker

Loaded data from Backblaze

Finding 1 - Failure rates by model

Seagate has the most failed models with 8 and HGST has the least with 3

Finding 2 - Failure signatures

Media / surface degradation has the most failures with 760 whereas Interface / timeout has the least with 1

Finding 3 - Individual failed drive

There were no clear signs of failure from the last thirty days until failure for a WD drive

When looking at another, there were clear signs of an issue starting 31 days prior to failure via smart 5,187,197, and 198. 

#Day 2 Findings

Corrected fleet AFR is 1.24%

The worst WD/HGST model was WUH721816ALE7L4 with an afr of 6.05%

23.4% of drives failed with no SMART warnings so they can't be predicted from SMART alone

#Day 3



System Prompt:
NULL means "not reported", never 0
Always state how many days of history were available
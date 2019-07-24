# Divergent Source Example

An example codebase specializing some small regions of code for individual platforms.

## Output
```
-----------------------
Platform Set LOC % LOC
-----------------------
       {CPU}  19 26.39
       {GPU}  11 15.28
  {GPU, CPU}  42 58.33
-----------------------
Code Divergence: 0.42
Unused Code (%): 0.00
Total SLOC: 72

Distance Matrix
--------------
     GPU  CPU
--------------
GPU 0.00 0.42
CPU 0.42 0.00
--------------
```

![dendrogram](./divergent-source-dendrogram.png)

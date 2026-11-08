# Usage: powershell -File tools\ghidra\oracle.ps1 <func_hex> [trials] [seed]
param([string]$f, [int]$n = 200, [int]$seed = 1)
$env:JAVA_HOME = 'C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot'
$g = 'E:\MANHUNT 2 DESCOMP\tools\ghidra_12.1.2_PUBLIC\support\analyzeHeadless.bat'
$p = 'E:\MK GOLD PC PORT'
& $g "$p\OUTPUT\ghidra" MKG -process 1ST_READ.elf -noanalysis -readOnly -scriptPath "$p\tools\ghidra" -postScript EmuOracle.java "$p\tests\oracle\specs\$f.spec" "$p\tests\oracle\vectors\$f.tsv" $n $seed *> "$p\OUTPUT\oracle_$f.log"
Select-String -Path "$p\OUTPUT\oracle_$f.log" -Pattern 'oracle runs|ERROR|Exception' | Select-Object -First 3

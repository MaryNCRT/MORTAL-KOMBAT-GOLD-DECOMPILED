# Usage: powershell -File tools\ghidra\dumpasm.ps1 <out.txt> <start:end> [...]
$env:JAVA_HOME = 'C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot'
$g = 'E:\MANHUNT 2 DESCOMP\tools\ghidra_12.1.2_PUBLIC\support\analyzeHeadless.bat'
$p = 'E:\MK GOLD PC PORT'
& $g "$p\OUTPUT\ghidra" MKG -process 1ST_READ.elf -noanalysis -readOnly -scriptPath "$p\tools\ghidra" -postScript DumpAsm.java @args *> "$p\OUTPUT\dumpasm.log"

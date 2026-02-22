$path = 'C:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
$lines = Get-Content -Path $path
# Line 4664 is index 4663
$lines[4663] = '        const participantsList = {{ participants | tojson | safe }};'
# Line 4665 is index 4664
$lines[4664] = '        // corrected multiline error'
# Line 4666 is index 4665
$lines[4665] = '        // end correction'
$lines | Set-Content -Path $path

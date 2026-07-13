# Generate a synthetic two-speaker dialogue wav using Windows built-in TTS.
# No downloads needed. Output: data/samples/dialogue.wav

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root "data\samples"
New-Item -ItemType Directory -Force $outDir | Out-Null
$outFile = Join-Path $outDir "dialogue.wav"

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $synth.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo.Name }
Write-Host "voices available: $($voices -join ', ')"

$male = $voices | Where-Object { $_ -match "David" } | Select-Object -First 1
$female = $voices | Where-Object { $_ -match "Zira|Hazel" } | Select-Object -First 1
if (-not $male -or -not $female) {
    if ($voices.Count -lt 2) { throw "need two TTS voices installed" }
    $male = $voices[0]; $female = $voices[1]
}
Write-Host "speaker A: $male"
Write-Host "speaker B: $female"

$dialogue = @(
    @($male,   "Good morning everyone, let's get started with the weekly sync."),
    @($female, "Sounds good. First up, the transcription service is now running on the new GPU box."),
    @($male,   "That is great news. How long does it take to process an hour of audio?"),
    @($female, "Roughly four minutes with the large model, and the speaker labels add about one more minute."),
    @($male,   "Impressive. Are we still planning to move it behind the reverse proxy this week?"),
    @($female, "Yes, the container image should be ready by Thursday, and then it joins the rest of the homelab."),
    @($male,   "Perfect. Anything blocking you at the moment?"),
    @($female, "Nothing blocking, but I would like a second pair of eyes on the merge logic before we tag a release.")
)

$synth.SetOutputToWaveFile($outFile)
foreach ($turn in $dialogue) {
    $synth.SelectVoice($turn[0])
    $synth.Speak($turn[1])
}
$synth.SetOutputToNull()
$synth.Dispose()

Write-Host "wrote $outFile"

[app]
title = Audio Recorder
package.name = audiorecorder  
package.domain = com.yorch.audiorecorder
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,plyer
android.permissions = RECORD_AUDIO,WRITE_EXTERNAL_STORAGE
android.minapi = 21
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1

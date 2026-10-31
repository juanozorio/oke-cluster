{{/*
Nome base do chart.
*/}}
{{- define "escala-servir.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Nome completo (fullname) dos recursos.
*/}}
{{- define "escala-servir.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart name + version (label).
*/}}
{{- define "escala-servir.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Labels comuns.
*/}}
{{- define "escala-servir.labels" -}}
helm.sh/chart: {{ include "escala-servir.chart" . }}
{{ include "escala-servir.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Labels de seleção.
*/}}
{{- define "escala-servir.selectorLabels" -}}
app.kubernetes.io/name: {{ include "escala-servir.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Tag da imagem: usa .Values.image.tag ou, se vazio, o appVersion do chart.
*/}}
{{- define "escala-servir.imageTag" -}}
{{- default .Chart.AppVersion .Values.image.tag }}
{{- end }}

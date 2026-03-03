{{/*
VeriRAG — Helm Template Helpers
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "verirag.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "verirag.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "verirag.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels (AZ-400 compliant).
*/}}
{{- define "verirag.labels" -}}
helm.sh/chart: {{ include "verirag.chart" . }}
{{ include "verirag.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: verirag
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "verirag.selectorLabels" -}}
app.kubernetes.io/name: {{ include "verirag.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "verirag.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "verirag.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host: local (containerized) or cloud (managed service).
*/}}
{{- define "verirag.pgHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "verirag.fullname" .) }}
{{- else }}
{{- required "postgresql.externalHost is required when postgresql.enabled=false" .Values.postgresql.externalHost }}
{{- end }}
{{- end }}

{{/*
Redis URL: local (containerized) or cloud (managed service).
*/}}
{{- define "verirag.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- .Values.redis.connectionUrl | default (printf "redis://%s-redis:6379/0" (include "verirag.fullname" .)) }}
{{- else }}
{{- required "redis.externalUrl is required when redis.enabled=false" .Values.redis.externalUrl }}
{{- end }}
{{- end }}

{{/*
Vault address: local (containerized) or omitted (cloud uses Azure Key Vault).
*/}}
{{- define "verirag.vaultAddr" -}}
{{- if .Values.vault.enabled }}
{{- .Values.vault.addr | default (printf "http://%s-vault:8200" (include "verirag.fullname" .)) }}
{{- else }}
{{- "" }}
{{- end }}
{{- end }}

{{- define "fraud-platform.api.fullname" -}}
{{ .Release.Name }}-api
{{- end }}

{{- define "fraud-platform.db.fullname" -}}
{{ .Release.Name }}-db
{{- end }}

{{- define "fraud-platform.frontend.fullname" -}}
{{ .Release.Name }}-frontend
{{- end }}

{{- define "fraud-platform.rabbitmq.fullname" -}}
{{ .Release.Name }}-rabbitmq
{{- end }}

{{- define "fraud-platform.redis.fullname" -}}
{{ .Release.Name }}-redis
{{- end }}

{{- define "fraud-platform.worker.fullname" -}}
{{ .Release.Name }}-worker
{{- end }}

{{- define "fraud-platform.mcp.fullname" -}}
{{ .Release.Name }}-mcp
{{- end }}



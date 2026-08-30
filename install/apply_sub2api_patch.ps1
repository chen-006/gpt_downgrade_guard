param(
  [string]$RepoPath = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
$Utf8 = [System.Text.UTF8Encoding]::new($false)

function Read-Text([string]$Path) {
  [System.IO.File]::ReadAllText($Path)
}

function Write-Text([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, $Utf8)
}

function Replace-Regex([string]$Path, [string]$Pattern, [string]$Replacement) {
  $Text = Read-Text $Path
  $Next = [regex]::Replace($Text, $Pattern, $Replacement)
  if ($Next -eq $Text) {
    throw "Replacement not found: $Path"
  }
  Write-Text $Path $Next
}

$Handler = Join-Path $RepoPath "backend/internal/handler/admin/account_handler.go"
$AccountTest = Join-Path $RepoPath "backend/internal/service/account_test_service.go"
$AccountUsage = Join-Path $RepoPath "backend/internal/service/account_usage_service.go"
$AdaptiveResponses = Join-Path $RepoPath "backend/internal/service/account_test_service_cn_adaptive.go"

Replace-Regex $Handler '(?s)type TestAccountRequest struct \{.*?AudioDataURL string `json:"audio_data_url"`\r?\n\}' @'
type TestAccountRequest struct {
	ModelID string `json:"model_id"`
	Prompt  string `json:"prompt"`
	Mode    string `json:"mode"`
	SystemPrompt    string `json:"system_prompt"`
	ReasoningEffort string `json:"reasoning_effort"`
	// Optional media for Grok (and future) real generation tests.
	// ImageDataURL / AudioDataURL are data:<mime>;base64,... payloads.
	ImageDataURL string `json:"image_data_url"`
	AudioDataURL string `json:"audio_data_url"`
}
'@

Replace-Regex $Handler '(?s)opts := service.AccountTestOptions\{\r?\n\t\tImageDataURL: req\.ImageDataURL,\r?\n\t\tAudioDataURL: req\.AudioDataURL,\r?\n\t\}' @'
	opts := service.AccountTestOptions{
		ImageDataURL: req.ImageDataURL,
		AudioDataURL: req.AudioDataURL,
		SystemPrompt: req.SystemPrompt,
		ReasoningEffort: req.ReasoningEffort,
	}
'@

Replace-Regex $AccountTest '(?s)type AccountTestOptions struct \{\r?\n\tImageDataURL string\r?\n\tAudioDataURL string\r?\n\}' @'
type AccountTestOptions struct {
	ImageDataURL string
	AudioDataURL string
	SystemPrompt string
	ReasoningEffort string
}
'@

Replace-Regex $AccountTest '(?s)case APIProtocolResponses:\s*return s\.testOpenAIAccountConnection\(c, account, modelID, prompt, normalizeAccountTestMode\(mode\)\)' @'
		case APIProtocolResponses:
			return s.testOpenAIAccountConnection(c, account, modelID, prompt, normalizeAccountTestMode(mode), testOpts.SystemPrompt, testOpts.ReasoningEffort)
'@

Replace-Regex $AccountTest '(?s)if account\.IsOpenAI\(\) \{\s*return s\.testOpenAIAccountConnection\(c, account, modelID, prompt, normalizeAccountTestMode\(mode\)\)\s*\}' @'
	if account.IsOpenAI() {
		return s.testOpenAIAccountConnection(c, account, modelID, prompt, normalizeAccountTestMode(mode), testOpts.SystemPrompt, testOpts.ReasoningEffort)
	}
'@

Replace-Regex $AccountTest '(?s)c\.Request = c\.Request\.WithContext\(markAgentIdentityTaskRecoveryTried\(ctx\)\)\s*return s\.testOpenAIAccountConnection\(c, account, modelID, prompt, mode\)' @'
			c.Request = c.Request.WithContext(markAgentIdentityTaskRecoveryTried(ctx))
			return s.testOpenAIAccountConnection(c, account, modelID, prompt, mode, systemPrompt, reasoningEffort)
'@

Replace-Regex $AccountTest 'func \(s \*AccountTestService\) testOpenAIAccountConnection\(c \*gin\.Context, account \*Account, modelID string, prompt string, mode string\) error \{' @'
func (s *AccountTestService) testOpenAIAccountConnection(c *gin.Context, account *Account, modelID string, prompt string, mode string, systemPrompt string, reasoningEffort string) error {
'@

Replace-Regex $AccountTest 'return s\.testOpenAIChatCompletionsConnection\(c, account, testModelID, prompt, normalizedBaseURL, authToken\)' @'
			return s.testOpenAIChatCompletionsConnection(c, account, testModelID, prompt, systemPrompt, reasoningEffort, normalizedBaseURL, authToken)
'@

Replace-Regex $AccountTest 'payload := createOpenAITestPayload\(upstreamTestModelID, isOAuth\)' @'
		payload := createOpenAITestPayload(upstreamTestModelID, prompt, systemPrompt, reasoningEffort, isOAuth)
'@

Replace-Regex $AccountTest '(?s)func \(s \*AccountTestService\) testOpenAIChatCompletionsConnection\(\r?\n\tc \*gin\.Context,\r?\n\taccount \*Account,\r?\n\ttestModelID string,\r?\n\tprompt string,\r?\n\tnormalizedBaseURL string,\r?\n\tauthToken string,\r?\n\) error \{' @'
func (s *AccountTestService) testOpenAIChatCompletionsConnection(
	c *gin.Context,
	account *Account,
	testModelID string,
	prompt string,
	systemPrompt string,
	reasoningEffort string,
	normalizedBaseURL string,
	authToken string,
) error {
'@

Replace-Regex $AccountTest 'payload := createOpenAIChatCompletionsTestPayload\(testModelID, prompt\)' @'
	payload := createOpenAIChatCompletionsTestPayload(testModelID, prompt, systemPrompt, reasoningEffort)
'@

Replace-Regex $AccountTest '(?s)func createOpenAITestPayload\(modelID string, isOAuth bool\) map\[string\]any \{.*?return payload\r?\n\}' @'
func createOpenAITestPayload(modelID string, prompt string, systemPrompt string, reasoningEffort string, isOAuth bool) map[string]any {
	payload := map[string]any{
		"model": modelID,
		"input": []map[string]any{
			{
				"role": "user",
				"content": []map[string]any{
					{
						"type": "input_text",
						"text": func() string {
							text := strings.TrimSpace(prompt)
							if text == "" {
								return "hi"
							}
							return text
						}(),
					},
				},
			},
		},
		"stream": true,
	}

	// OAuth accounts using ChatGPT internal API require store: false
	if isOAuth {
		payload["store"] = false
	}

	if text := strings.TrimSpace(systemPrompt); text != "" {
		payload["instructions"] = text
	} else {
		payload["instructions"] = openai.DefaultInstructions
	}
	if effort := strings.TrimSpace(reasoningEffort); effort != "" {
		payload["reasoning"] = map[string]any{"effort": effort}
	}

	return payload
}
'@

Replace-Regex $AccountTest '(?s)func createOpenAIChatCompletionsTestPayload\(modelID string, prompt string\) map\[string\]any \{\s*testPrompt := strings\.TrimSpace\(prompt\)\s*if testPrompt == "" \{\s*testPrompt = "hi"\s*\}\s*return map\[string\]any\{\s*"model": modelID,\s*"messages": \[\]map\[string\]any\{\s*\{\s*"role":\s*"user",\s*"content": testPrompt,\s*\},\s*\},\s*"stream": true,\s*\}\s*\}' @'
func createOpenAIChatCompletionsTestPayload(modelID string, prompt string, systemPrompt string, reasoningEffort string) map[string]any {
	messages := []map[string]any{}
	if text := strings.TrimSpace(systemPrompt); text != "" {
		messages = append(messages, map[string]any{"role": "system", "content": text})
	}
	testPrompt := strings.TrimSpace(prompt)
	if testPrompt == "" {
		testPrompt = "hi"
	}
	messages = append(messages, map[string]any{"role": "user", "content": testPrompt})

	payload := map[string]any{
		"model":   modelID,
		"messages": messages,
		"stream":  true,
	}
	if effort := strings.TrimSpace(reasoningEffort); effort != "" {
		payload["reasoning_effort"] = effort
	}
	return payload
}
'@

Replace-Regex $AccountUsage 'payload := createOpenAITestPayload\(modelID, true\)' @'
	payload := createOpenAITestPayload(modelID, "", "", "", true)
'@

Replace-Regex $AdaptiveResponses 'payload := createOpenAITestPayload\(testModelID, false\)' @'
	payload := createOpenAITestPayload(testModelID, "", "", "", false)
'@

Write-Host "Sub2 API patch applied. Restart Sub2 API."

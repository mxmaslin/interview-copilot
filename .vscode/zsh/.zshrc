# Powerlevel10k: instant prompt только в корневом ZDOTDIR/.zshrc (не в sourced ~/.zshrc).
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export VIRTUAL_ENV_DISABLE_PROMPT=1

# Остаток ~/.zshrc без блока instant prompt (строки 1–7).
if [[ -f "${HOME}/.zshrc" ]]; then
  source <(command sed '1,7d' "${HOME}/.zshrc")
fi

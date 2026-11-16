# Labubu Survival — Pygame + TikTokLive

Jogo de sobrevivência com Labubu, monstros, ataques automáticos e eventos de live.

## Instalação (Windows)

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py main.py
```

Para conectar à live: `py main.py --username SEU_USUARIO`.

## Recursos necessários

O jogo carrega `assets/labubu_front.png`, `assets/labubu_back.png`, `assets/labubu_left.png` e `assets/labubu_right.png`. O STL original pode ficar em `assets/labubu.stl`. Esses arquivos binários ainda precisam ser adicionados ao repositório.

## Eventos

- Rosa: cura
- Leão/Universo: explosão e escudo
- Outros presentes: invocam monstros
- Comentários: `cima`, `baixo`, `esquerda`, `direita`, `bomba`, `curar`, `escudo`, `monstro`
- 25 curtidas: ataque em área
- Seguidor: cria um guardião temporário

Controles: WASD/setas para andar, espaço para dash, P para pausar, Enter para reiniciar, Esc para sair.

TikTokLive é uma biblioteca não oficial; a disponibilidade dos eventos depende da plataforma e da versão instalada.

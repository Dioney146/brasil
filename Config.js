// Configuração dos estados e das URLs publicadas (CSV) de cada aba HISTORICO_<estado>
//
// Como pegar a URL de cada estado:
// 1. Na planilha Google, publique a aba HISTORICO_<estado> na web:
//    Arquivo > Compartilhar > Publicar na Web > selecione a aba > formato "Valores separados por vírgula (.csv)" > Publicar
// 2. Copie a URL gerada (algo como .../pubhtml?gid=XXXX&single=true)
// 3. Troque "pubhtml" por "pub" e adicione "&output=csv" no final
//    Exemplo final: https://docs.google.com/spreadsheets/d/e/CHAVE/pub?gid=XXXX&single=true&output=csv
// 4. Cole a URL final abaixo, no estado correspondente

const CONFIG_ESTADOS = {
  AM: {
    nome: "Amazonas",
    csvUrl: "https://docs.google.com/spreadsheets/d/e/2PACX-1vR2XlWGFoKPGlo9p8COnOjenyUrl-gZJC1pdzmzut1BVZFnwY7zJ2_9PRz5CYhHXITswB3JvNohSxkE/pub?gid=119371517&single=true&output=csv"
  },
  BA: {
    nome: "Bahia",
    csvUrl: ""
  },
  DF: {
    nome: "Distrito Federal",
    csvUrl: ""
  },
  MG: {
    nome: "Minas Gerais",
    csvUrl: ""
  },
  SP: {
    nome: "São Paulo",
    csvUrl: ""
  },
  SPW: {
    nome: "São Paulo (SPW)",
    csvUrl: ""
  }
};

"""Conteúdos padrão utilizados para preencher páginas essenciais do portal."""

DEFAULT_PAGES = [
    {
        "slug": "licitacoes",
        "title": "Editais e Licitações",
        "content": (
            "<p>Consulte aqui os editais de licitação em andamento e os resultados já publicados. "
            "As licitações seguem a legislação vigente e garantem a transparência dos gastos públicos.</p>"
            "<h3>Editais em andamento</h3>"
            "<ul>"
            "<li><strong>Pregão Eletrônico 12/2024:</strong> Aquisição de medicamentos para a rede municipal de saúde.</li>"
            "<li><strong>Concorrência 05/2024:</strong> Obras de recuperação de vias urbanas e estradas vicinais.</li>"
            "<li><strong>Tomada de Preços 03/2024:</strong> Serviços de manutenção predial preventiva.</li>"
            "</ul>"
            "<p>Os editais completos podem ser consultados presencialmente na Divisão de Compras ou solicitados pelo e-mail licitacoes@orlandia.sp.gov.br.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "concursos",
        "title": "Concursos Públicos",
        "content": (
            "<p>Confira os concursos públicos e processos seletivos promovidos pela Prefeitura de Orlândia.</p>"
            "<h3>Oportunidades abertas</h3>"
            "<ul>"
            "<li><strong>Concurso 01/2024:</strong> Inscrições até 30/05 para cargos de Saúde, Educação e Administração.</li>"
            "<li><strong>Processo Seletivo Simplificado:</strong> Cadastro reserva para profissionais de apoio escolar.</li>"
            "</ul>"
            "<p>Os editais estão disponíveis para download no portal. Dúvidas podem ser enviadas para concursos@orlandia.sp.gov.br.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "iptu-online",
        "title": "IPTU Online",
        "content": (
            "<p>Emita a segunda via do seu carnê de IPTU e consulte débitos utilizando o serviço on-line.</p>"
            "<ol>"
            "<li>Acesse o sistema com o número de inscrição imobiliária.</li>"
            "<li>Selecione o exercício desejado para gerar o boleto.</li>"
            "<li>Efetue o pagamento na rede bancária conveniada ou por internet banking.</li>"
            "</ol>"
            "<p>Para negociar débitos em atraso, procure o setor de Tributação presencialmente ou pelo e-mail tributacao@orlandia.sp.gov.br.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "alvaras",
        "title": "Emissão de Alvarás",
        "content": (
            "<p>Solicite alvarás de funcionamento, construção e regularização diretamente com a equipe técnica da Prefeitura.</p>"
            "<h3>Documentos necessários</h3>"
            "<ul>"
            "<li>Requerimento padrão preenchido e assinado pelo responsável.</li>"
            "<li>Cópia do CPF/CNPJ e comprovante de endereço atualizado.</li>"
            "<li>Planta ou croqui do imóvel, quando aplicável.</li>"
            "</ul>"
            "<p>Os pedidos podem ser acompanhados pelo e-mail desenvolvimento@orlandia.sp.gov.br.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "acesso-informacao",
        "title": "Acesso à Informação",
        "content": (
            "<p>Este canal garante o cumprimento da Lei de Acesso à Informação. Consulte relatórios, contratos e perguntas frequentes.</p>"
            "<p>Envie sua solicitação formal preenchendo o formulário eletrônico disponível e acompanhe o protocolo pelo e-mail informado.</p>"
            "<p>Prazo de resposta: até 20 dias prorrogáveis conforme a legislação federal.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "cidadao-web",
        "title": "Portal Cidadão Web",
        "content": (
            "<p>Reúna em um só lugar os serviços digitais disponibilizados pela Prefeitura.</p>"
            "<ul>"
            "<li>Emissão de certidões negativas.</li>"
            "<li>Acompanhamento de protocolos e requerimentos.</li>"
            "<li>Atualização cadastral de contribuintes.</li>"
            "</ul>"
            "<p>Crie sua conta utilizando o CPF e mantenha seus dados atualizados para receber notificações.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "portal-transparencia",
        "title": "Portal da Transparência",
        "content": (
            "<p>Acompanhe as receitas, despesas, contratos e indicadores fiscais do município.</p>"
            "<h3>Principais consultas</h3>"
            "<ul>"
            "<li>Execução orçamentária diária.</li>"
            "<li>Folha de pagamento detalhada por secretaria.</li>"
            "<li>Convênios e parcerias vigentes.</li>"
            "</ul>"
            "<p>Os dados são atualizados mensalmente e podem ser exportados em formato aberto.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "jornal-oficial",
        "title": "Jornal Oficial",
        "content": (
            "<p>Disponibilizamos as edições digitais do Jornal Oficial do Município.</p>"
            "<p>Faça o download das publicações recentes e acompanhe decretos, leis e atos administrativos.</p>"
            "<ul>"
            "<li>Edição 312 - 15/04/2024.</li>"
            "<li>Edição 311 - 08/04/2024.</li>"
            "<li>Edição 310 - 01/04/2024.</li>"
            "</ul>"
        ),
        "visible": False,
    },
    {
        "slug": "consulta-cep",
        "title": "Consulta de CEP",
        "content": (
            "<p>Utilize este serviço para identificar o CEP de ruas, avenidas e bairros de Orlândia.</p>"
            "<p>Informe o nome da via ou o número do imóvel e visualize o CEP correspondente.</p>"
            "<p>Para solicitações especiais entre em contato com a Secretaria de Planejamento.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "glossario-termos",
        "title": "Glossário de Termos Públicos",
        "content": (
            "<p>Entenda os conceitos mais utilizados nas publicações oficiais.</p>"
            "<dl>"
            "<dt>LOA</dt><dd>Lei Orçamentária Anual que define receitas e despesas do exercício.</dd>"
            "<dt>LDO</dt><dd>Lei de Diretrizes Orçamentárias que orienta a elaboração da LOA.</dd>"
            "<dt>PPA</dt><dd>Plano Plurianual que estabelece objetivos para quatro anos.</dd>"
            "</dl>"
        ),
        "visible": False,
    },
    {
        "slug": "cirurgia-eletiva",
        "title": "Cirurgia Eletiva",
        "content": (
            "<p>Saiba como solicitar cirurgias eletivas pelo Sistema Único de Saúde no município.</p>"
            "<ol>"
            "<li>Procure a unidade básica de saúde para avaliação médica.</li>"
            "<li>Entregue a documentação exigida e aguarde o agendamento.</li>"
            "<li>Acompanhe a posição na fila pelo telefone (16) 3820-2050.</li>"
            "</ol>"
            "<p>Os casos são priorizados conforme critérios clínicos e protocolos do SUS.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "estudante-universitario",
        "title": "Programa Estudante Universitário",
        "content": (
            "<p>Benefícios destinados aos alunos de graduação residentes em Orlândia.</p>"
            "<ul>"
            "<li>Auxílio-transporte com cadastro anual.</li>"
            "<li>Bolsa de estudos para famílias de baixa renda.</li>"
            "<li>Parcerias com instituições de ensino para descontos em mensalidades.</li>"
            "</ul>"
            "<p>As inscrições são realizadas na Secretaria de Educação entre março e abril.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "programa-assistencia-social",
        "title": "Programa de Assistência Social Integral",
        "content": (
            "<p>O novo programa amplia a rede de proteção a famílias em situação de vulnerabilidade.</p>"
            "<p>As equipes de assistência realizarão visitas domiciliares, encaminhamentos para serviços de saúde e capacitações profissionais.</p>"
            "<p>Interessados devem procurar o CRAS mais próximo ou ligar para (16) 3820-2105.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "indice-saneamento",
        "title": "Melhoria do Índice de Saneamento",
        "content": (
            "<p>Orlândia alcançou 98% de cobertura de água tratada e esgoto sanitário.</p>"
            "<p>O resultado é fruto de investimentos em ampliação de redes, novos reservatórios e campanhas de uso consciente de água.</p>"
            "<p>As obras continuam nos bairros Jardim Boa Vista e Cidade Alta para atingir 100% de atendimento.</p>"
        ),
        "visible": False,
    },
    {
        "slug": "cursos-tecnicos",
        "title": "Cursos Técnicos da Secretaria de Educação",
        "content": (
            "<p>Estão abertas as inscrições para cursos técnicos em parceria com o Centro Paula Souza.</p>"
            "<ul>"
            "<li>Administração</li>"
            "<li>Informática para Internet</li>"
            "<li>Enfermagem</li>"
            "</ul>"
            "<p>As vagas são limitadas e as aulas começam em agosto. Inscreva-se pelo formulário on-line até 25/05.</p>"
        ),
        "visible": False,
    },
]

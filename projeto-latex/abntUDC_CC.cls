% !TeX encoding = UTF-8

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%                                                                          
%% Customizações do abnTeX2 (http://abnTeX2.googlecode.com) para o          
%% Curso de Ciência da Computação do Centro Universitário União             
%% Dinâmica das Cataratas - UDC.                                            
%%                                                                          
%% This work may be distributed and/or modified under the
%% conditions of the LaTeX Project Public License, either version 1.3
%% of this license or (at your option) any later version.
%% The latest version of this license is in
%%   http://www.latex-project.org/lppl.txt
%% and version 1.3 or later is part of all distributions of LaTeX
%% version 2005/12/01 or later.
%%                                                                          
%%                                                                          
%% The Current Maintainer of this work is Miguel Matrakas, mdmatrakas@gmail.com
%%                                                                          
%% Further information about abnTeX2 are available on
%% https://github.com/abntex/abntex2/wiki
%%                                                                          
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% $Log: cvs-id.def,v $
%% Revision 1.3  2003/10/13 09:41:42  gweber
%% Adicionado \CVSClass e \CVSFile
%%
%% Revision 1.2  2003/10/10 10:05:51  gweber
%% Corrigido argumento em \CVSPackage
%%
%% Revision 1.1  2003/10/10 10:01:07  gweber
%% Arquivo que provê os comandos para extrair informações geradas automaticamente
%% pelo CVS tal como data, revisão etc.
%%

\NeedsTeXFormat{LaTeX2e}

\input{cvs-id.def}
\CVSExtract$Id: abnt-UDC-CC.cls,v 1.3 2019/10/26 11:22:00 mdmatrakas Exp $
\CVSPackage{abntUDC_CC}{} %\ProvidesPackage

\PassOptionsToClass{pagestart=firstchapter,chapter=TITLE,section=TITLE}{abntex2}

%\ProvidesClass{cc-udc-abntex2}[2018/06/24 v1.2 Modelo do Curso de Ci\^encia do Centro Universitário Din\^amica das Cataratas (UDC), baseado em abnTeX2]
\ProvidesClass{cc-udc-abntex2}

%
% Repassa todos os parametros a classe abntex2, 
\DeclareOption*{%
  \PassOptionsToClass{\CurrentOption}{abntex2}%
}
\ProcessOptions\relax
\LoadClass{abntex2}

%=====
% Dependencias
%=====
\RequirePackage{etoolbox}	% macro \patchcmd utilizada p configurar o sumário
\RequirePackage{listings} 	% Formatação de código fonte - Java, C++, etc
\RequirePackage{color}		% Controle das cores
\RequirePackage{lastpage}	% Usado pela Ficha catalográfica
\RequirePackage{lmodern}    % Usa a font Latin Modern

\RequirePackage{ifthen}
%\RequirePackage{sectsty}	% Disponibiliza a macro \MakeUppercase para colocar os títulos em caixa alta
%\usepackage[explicit]{titlesec} % Para formatação das seções e subseções em maiúsculas
%\usepackage{lipsum}

\newcommand{\ifnotempty}[2]{\ifthenelse{\not\equal{#1}{}}{#2}{}}


\local{Foz do Igua{\c c}u}
\instituicao{Centro Universit{\' a}rio Din{\^ a}mica das Cataratas}
\tipotrabalho{Trabalho de Conclus{\~a}o de Curso}

% Comandos de dados - nome autor para citacao
\providecommand{\imprimirinstituicaoSigla}{}
\newcommand{\instituicaoSigla}[1]{\renewcommand{\imprimirinstituicaoSigla}{#1}}
\instituicaoSigla{UDC}

% Comandos de dados - nome do curso
\providecommand{\imprimircurso}{}
\newcommand{\curso}[1]{\renewcommand{\imprimircurso}{#1}}
\curso{Ci{\^ e}ncia da Computa{\c c}{\~ a}o}

% Comandos de dados - nome do segundo autor
\providecommand{\imprimirsegundoautor}{}
\newcommand{\segundoautor}[1]{\renewcommand{\imprimirsegundoautor}{#1}}

% Comandos de dados - nome do autor como citado
\providecommand{\imprimirautorcitado}{}
\newcommand{\autorcitado}[1]{\renewcommand{\imprimirautorcitado}{#1}}

% Comandos de dados - nome do segundo autor como citado
\providecommand{\imprimirsegundoautorcitado}{}
\newcommand{\segundoautorcitado}[1]{\renewcommand{\imprimirsegundoautorcitado}{#1}}

% Comandos de dados - codigo do autor
\providecommand{\imprimircodigoautor}{}
\newcommand{\codigoautor}[1]{\renewcommand{\imprimircodigoautor}{#1}}

% Comandos de dados - codigo da publicacao
\providecommand{\imprimircodigopublicacao}{}
\newcommand{\codigopublicacao}[1]{\renewcommand{\imprimircodigopublicacao}{#1}}

% Comandos de dados - palavra chave um
\providecommand{\imprimirpalavrachaveum}{}
\newcommand{\palavrachaveum}[1]{\renewcommand{\imprimirpalavrachaveum}{#1}}

% Comandos de dados - palavra chave dois
\providecommand{\imprimirpalavrachavedois}{}
\newcommand{\palavrachavedois}[1]{\renewcommand{\imprimirpalavrachavedois}{#1}}

% Comandos de dados - palavra chave tres
\providecommand{\imprimirpalavrachavetres}{}
\newcommand{\palavrachavetres}[1]{\renewcommand{\imprimirpalavrachavetres}{#1}}


\preambulo{Trabalho de conclus{\~ a}o de curso apresentado como requisito obrigat{\' o}rio para obten{\c c}{\~ a}o do t{\' i}tulo de Bacharel em \imprimircurso do \imprimirinstituicao.}

% ---
% CAPA
% ---

\renewcommand{\imprimircapa}{%
  \begin{capa} \makeatletter
    \center
	{\textbf{ \large{ \MakeUppercase{\imprimirinstituicao} } } }

    { \normalsize\MakeUppercase{\imprimirautor } }
    
    { \normalsize\MakeUppercase{\imprimirsegundoautor } }

    \vspace*{8cm}
    { \ABNTEXchapterfont\bfseries\large\MakeUppercase{\imprimirtitulo} }
    \vfill
    
    { \normalfont\small\MakeUppercase{\imprimirlocal} }

    { \normalfont\small\imprimirdata }
    
    \vspace*{1cm} 
    \makeatother
  \end{capa}
}

% ---
% FOLHA DE ROSTO
% ---
\renewcommand{\folhaderostocontent}{
		\center	
		{ \normalsize\MakeUppercase{\imprimirautor} }
    
		{ \normalsize\MakeUppercase{\imprimirsegundoautor } }
	
	    \vspace*{8cm}		
		
		{\large\MakeUppercase{\imprimirtitulo}}
	
		\vspace*{3cm}	

		\abntex@ifnotempty{\imprimirpreambulo}{
			\hspace{.45\textwidth}
			\begin{minipage}{.5\textwidth}
				{ \footnotesize \SingleSpacing
				  \imprimirpreambulo				
				  \SingleSpacing				
				  {\imprimirorientadorRotulo~\imprimirorientador\par }
				  \SingleSpacing	
		          \abntex@ifnotempty{\imprimircoorientador}{
		              {\imprimircoorientadorRotulo~\imprimircoorientador} } 
	            }
			\end{minipage}
		
			\vspace*{\fill}
		}
		
		{\normalfont\small\MakeUppercase{\imprimirlocal}}
		
		{\normalfont\small\imprimirdata}		
}
\makeatother


% ---
% FICHA CATALOGRAFICA
% ---
%\newenvironment{fichacatalografica}

\newcommand{\imprimirfichacatalografica}{
%	\begin{fichacatalografica}
		%\vspace*{15cm}       %  Posição  vertical
		\ \vfill
		
		\hrule %  Linha  horizontal
		
		\begin{center}       %  Minipage  Centralizado
			\imprimircodigoautor \hspace{1cm}			
			\begin{minipage}[t]{12.5cm}  %  Largura
				%\SingleSpacing
				\imprimirautorcitado{\ifnotempty{\imprimirsegundoautorcitado}{; \imprimirsegundoautorcitado} } % Nome de referência. Por ex. Silva, João Paulo
				
				\hspace{0.5cm}  \imprimirtitulo~/~\imprimirautor \ifnotempty{\imprimirsegundoautor}{, \imprimirsegundoautor} ~--~ \imprimirlocal,  \imprimirdata.
				
				\hspace{0.5cm}  \pageref{LastPage} f. :  il. color.;
				
				\hspace{0.5cm}  \imprimirtipotrabalho~--~\imprimirinstituicao ~(\imprimirinstituicaoSigla). \imprimirdata.
				
				\hspace{0.5cm}  \imprimirorientadorRotulo ~\imprimirorientador
				
				\ifnotempty{\imprimircoorientador}{%
					\hspace{0.5cm}  \imprimircoorientadorRotulo ~\imprimircoorientador }
				
				\hspace{0.5cm}  Bibliografia: p. \pageref{biblio} ~--~ \pageref{fimBiblio}
							
				\hspace{0.5cm}
				1.  \imprimirpalavrachaveum.
				2.  \imprimirpalavrachavedois.
				3.  \imprimirpalavrachavetres.
				I.  \imprimirorientador\ifnotempty{\imprimircoorientador}{, \imprimircoorientador}.
				II.  \imprimirinstituicao.
				III. \imprimircurso.
				IV. \imprimirtitulo
				
				\hspace{8.75cm}  \imprimircodigopublicacao   %CDU 02:141:005.7
				
			\end{minipage}
		\end{center}
		\hrule
%	\end{fichacatalografica}
}


%==============================================================================
% outras configurações
%==============================================================================



\setlength{\parindent}{1.5cm} % Identação da primeira linha do parágrafo
\setlength{\parskip}{0cm}  % Controle do espaçamento entre parágrafos

% Controle do espaçamento entre a legenda e a fonte (e nota) de figuras e tabelas}:
\setlength{\abovecaptionskip}{1 mm}
\setlength{\belowcaptionskip}{1 mm}
%----------------------------------------------------------------------------- 
%----------------------------------------------------------------------------- 
% Define os tamanhos das margens do documento
\setlrmarginsandblock{3cm}{2cm}{*}
\setulmarginsandblock{3cm}{2cm}{*}
\checkandfixthelayout


%-----------------------------------------------------------------------------
% CONFIGURACAO DO ESTILO DE PÁGINA TEXTUAL 
%-----------------------------------------------------------------------------
%%criar um novo estilo de cabeçalhos e rodapés
\makepagestyle{abnt_CC-UDC}
  %%cabeçalhos
  \makeevenhead{abnt_CC-UDC}{\ABNTEXfontereduzida\thepage}{}{}
  \makeoddhead{abnt_CC-UDC}{}{}{\ABNTEXfontereduzida\thepage}
  %\makeheadrule{textualCC-Anglo}{\textwidth}{\normalrulethickness} %linha
  %% rodapé
  \makeevenfoot{abnt_CC-UDC}{}{}{} 
  \makeoddfoot{abnt_CC-UDC}{}{}{}
\pagestyle{abnt_CC-UDC}


\newtheorem{theorem}{Teorema}[chapter]
\newtheorem{definition}[theorem]{Defini\c{c}\~{a}o}
\newtheorem{proposition}[theorem]{Proposi\c{c}\~{a}o}

\makeatother


%----------------------------------------------------------------------------- 
% Definição das configurações de fonte para de part, chapter, section, 
% subsection e subsubsection
%----------------------------------------------------------------------------- 
\renewcommand{\ABNTEXpartfont}{\normalfont\bfseries\large}
\renewcommand{\ABNTEXpartfontsize}{\large}

\renewcommand{\ABNTEXchapterfont}{\normalfont\bfseries}
\renewcommand{\ABNTEXchapterfontsize}{\normalsize}

\renewcommand{\ABNTEXsectionfont}{\normalfont}
\renewcommand{\ABNTEXsectionfontsize}{\normalsize}

\renewcommand{\ABNTEXsubsectionfont}{\normalfont\bfseries}
\renewcommand{\ABNTEXsubsectionfontsize}{\normalsize}

\renewcommand{\ABNTEXsubsubsectionfont}{\normalfont\itshape}
\renewcommand{\ABNTEXsubsubsectionfontsize}{\normalsize}

\renewcommand{\ABNTEXsubsubsubsectionfont}{\normalfont}
\renewcommand{\ABNTEXsubsubsubsectionfontsize}{\normalsize}

%-----------------------------------------------------------------------------
% CONFIGURACAO DO SUMARIO
%-----------------------------------------------------------------------------
% Modifica as fontes do sumário
\renewcommand*{\cftpartfont}{\normalfont\bfseries\large}
\renewcommand*{\cftchapterfont}{\normalfont\bfseries}
\renewcommand*{\cftsectionfont}{\normalfont}
\renewcommand*{\cftsubsectionfont}{\normalfont\bfseries}
\renewcommand*{\cftsubsubsectionfont}{\normalfont\itshape}
\renewcommand*{\cftparagraphfont}{\normalfont}

% Modifica o espaçamento no sumário
% Nao ha espacos, exceto para as entradas de capitulos
\setlength{\cftbeforechapterskip}{\onelineskip}
\setlength{\cftbeforesectionskip}{0pt}
\setlength{\cftbeforesubsectionskip}{0pt}
\setlength{\cftbeforesubsubsectionskip}{0pt}
\setlength{\cftbeforeparagraphskip}{0pt}


% Indica se os nomes de capítulo e seção devem estar em maiúsculas ou não
\setboolean{ABNTEXupperchapter}{true}
\setboolean{ABNTEXuppersection}{true}
\setboolean{ABNTEXuppersubsection}{false}
\setboolean{ABNTEXuppersubsubsection}{false}
\setboolean{ABNTEXuppersubsubsubsection}{false}

%---------------------------------------------------------------------------- 
% CONFIGURAÇÃO DE LISTAS DE CONTEÚDO
% ---
% lista de gráficos
% -
\newcommand{\graficoname}{GR{\'A}FICO}
\newcommand{\graficoautorefname}{Gr{\'a}fico}
\newcommand{\listofgraficosname}{LISTA DE GR{\' A}FICOS}
\newfloat[chapter]{grafico}{logr}{\graficoname}
\newlistof{listofgraficos}{logr}{\listofgraficosname}
\newlistentry{grafico}{logr}{0}
\counterwithout{grafico}{chapter}		% atende às regras da ABNT em listas
\renewcommand{\cftgraficoname}{\graficoname\space}
\renewcommand*{\cftgraficoaftersnum}{\hfill--\hfill}

% lista de códigos
% -
\renewcommand{\lstlistingname}{C{\'O}DIGO}
\renewcommand{\lstlistlistingname}{LISTA DE C{\'O}DIGOS}
\newcommand{\lstnumberautorefname}{C{\'o}digo}

% configurações para atender às regras da ABNT em listas
\begingroup\makeatletter				
\let\newcounter\@gobble\let\setcounter\@gobbletwo
  \globaldefs\@ne \let\c@loldepth\@ne
  \newlistof{listings}{lol}{\lstlistlistingname}
  \newlistentry{lstlisting}{lol}{0}
\endgroup

\renewcommand{\cftlstlistingaftersnum}{\hfill--\hfill}

\let\oldlstlistoflistings\lstlistoflistings
\renewcommand{\lstlistoflistings}{%
   \begingroup%
   \let\oldnumberline\numberline%
   \renewcommand{\numberline}{\lstlistingname\space\oldnumberline}%
   \oldlstlistoflistings%
   \endgroup}



%----------------------------------------------------------------------------- 
% Nomes constantes do abnTeX2 em portugues (definições padrões)
%----------------------------------------------------------------------------- 
	%% ajusta nomes padrões do babel
\addto\captionsbrazil{
	% CAPITALIZAÇÃO DE LISTAS
	\renewcommand{\bibname}{REFER{\^ E}NCIAS}
	\renewcommand{\indexname}{{\'I}NDICE}
	\renewcommand{\listadesiglasname}{LISTA DE ABREVIATURAS}
	\renewcommand{\listfigurename}{LISTA DE ILUSTRA{\c{C}}{\~{O}}ES}
	\renewcommand{\listtablename}{LISTA DE TABELAS}
	\renewcommand{\contentsname}{SUM{\'A}RIO}
	\renewcommand{\appendixtocname}{AP{\^E}NDICES}
	\renewcommand{\appendixpagename}{AP{\^E}NDICES}
	\renewcommand{\anexosname}{ANEXOS}
	\renewcommand{\apendicesname}{AP{\^E}NDICES}
	%% ajusta nomes
	\renewcommand{\folhadeaprovacaoname}{Termo de Aprovação}
	\renewcommand{\orientadorname}{Orientador:}
	\renewcommand{\coorientadorname}{Coorientador:}
	\renewcommand{\figurename}{FIGURA}
	\renewcommand{\tablename}{TABELA}
	\renewcommand{\fontename}{FONTE}
	\renewcommand{\notaname}{NOTA}
	%% ajusta nomes usados com a macro \autoref
	\renewcommand{\figureautorefname}{Figura}
	\renewcommand{\tableautorefname}{Tabela}
	\renewcommand{\partautorefname}{Parte}
	\renewcommand{\chapterautorefname}{Cap{\'i}tulo}
	\renewcommand{\sectionautorefname}{Se{\c c}\~ao}
	\renewcommand{\subsectionautorefname}{Subse{\c c}\~ao}
	\renewcommand{\subsubsectionautorefname}{Subse{\c c}\~ao}
	\renewcommand{\pageautorefname}{P{\'a}gina}
	\renewcommand{\paragraphautorefname}{Par{\'a}grafo}
	\renewcommand{\equationautorefname}{Equa{\c c}{\~a}o}
}

% Indica se os nomes de capítulo e seção devem estar em maiúsculas ou não
\setboolean{ABNTEXupperchapter}{true}
\setboolean{ABNTEXuppersection}{true}
\setboolean{ABNTEXuppersubsection}{false}
\setboolean{ABNTEXuppersubsubsection}{false}
\setboolean{ABNTEXuppersubsubsubsection}{false}

%---------------------------------------------------------------------------- 
% DEFINIÇÃO DE NOMES DE CORES
%---------------------------------------------------------------------------- 
\definecolor{codegreen}{rgb}{0,0.6,0}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
\definecolor{whitesmoke}{rgb}{0.96, 0.96, 0.96}
\definecolor{deepcarminepink}{rgb}{0.94, 0.19, 0.22}
\definecolor{tearose(orange)}{rgb}{0.97, 0.51, 0.47}
\definecolor{tealgreen}{rgb}{0.0, 0.51, 0.5}
\definecolor{teagreen}{rgb}{0.82, 0.94, 0.75}
\definecolor{tealblue}{rgb}{0.21, 0.46, 0.53}
\definecolor{blue}{RGB}{41,5,195}% alterando o aspecto da cor azul

% Caracteres acentuados para uso nos ambientes de códigos fonte
\makeatother
\lstset{%
        inputencoding=utf8,
        extendedchars=true,
        literate=%
        {é}{{\'{e}}}1
        {è}{{\`{e}}}1
        {ê}{{\^{e}}}1
        {ë}{{\¨{e}}}1
        {É}{{\'{E}}}1
        {Ê}{{\^{E}}}1
        {û}{{\^{u}}}1
        {ù}{{\`{u}}}1
        {ú}{{\'{u}}}1
        {ü}{{\¨{u}}}1
        {â}{{\^{a}}}1
        {à}{{\`{a}}}1
        {á}{{\'{a}}}1
        {ã}{{\~{a}}}1
        {Á}{{\'{A}}}1
        {Â}{{\^{A}}}1
        {Ã}{{\~{A}}}1
        {ç}{{\c{c}}}1
        {Ç}{{\c{C}}}1
        {õ}{{\~{o}}}1
        {ó}{{\'{o}}}1
        {ô}{{\^{o}}}1
        {Õ}{{\~{O}}}1
        {Ó}{{\'{O}}}1
        {Ô}{{\^{O}}}1
        {î}{{\^{i}}}1
        {Î}{{\^{I}}}1
        {í}{{\'{i}}}1
        {Í}{{\~{Í}}}1
}

% Define a formatação de código fonte do Tex
\newcommand{\codigoTex}{%
\lstset{%
	language=[LaTeX]TeX,%
    basicstyle=\linespread{0.94}\ttfamily\footnotesize,%
    breaklines=true,%
    prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
    showtabs=false,%
    showspaces=false,%
    showstringspaces=false,%
    backgroundcolor=\color{whitesmoke},   
    commentstyle=\color{codegreen},
    keywordstyle=\color{deepcarminepink}\bfseries,
    numberstyle=\tiny\color{tealblue},
    stringstyle=\color{tealgreen}\itshape,
    basicstyle=\footnotesize,
    numbers=left,%
	fancyvrb=true,%
	mathescape=true,%    
	captionpos=t,%
    escapeinside={\%*}{*)},%
    numbersep=5pt,              
    firstnumber=1,    
    tabsize=2
}
}

% Define a formatação de código fonte da linguagem Java
\newcommand{\codigoJava}{%
\lstset{%
    language=Java,%
	backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
	breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
	breaklines=true,                 % sets automatic line breaking
	keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
	keywordstyle=\color{blue},       % keyword style
	numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
	numbersep=5pt,                   % how far the line-numbers are from the code
	rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
	showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
	showstringspaces=false,          % underline spaces within strings only
	showtabs=false,                  % show tabs within strings adding particular underscores
	stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
	tabsize=2,	                   % sets default tabsize to 2 spaces
	basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
	prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
	commentstyle=\color{codegreen},
	keywordstyle=\color{deepcarminepink}\bfseries,
	numberstyle=\tiny\color{tealblue},
	stringstyle=\color{tealgreen}\itshape,
	numbers=left,%
	captionpos=t,%
	firstnumber=1,
	escapeinside={\%*}{*)},%
}
}

% Define a formatação de código fonte da linguagem C
\newcommand{\codigoC}{%
\lstset{%
	language=C,                 % the language of the code
	backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
	%basicstyle=\footnotesize,        % the size of the fonts that are used for the code
	breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
	breaklines=true,                 % sets automatic line breaking
	keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
	keywordstyle=\color{blue},       % keyword style
	numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
	numbersep=5pt,                   % how far the line-numbers are from the code
	rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
	showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
	showstringspaces=false,          % underline spaces within strings only
	showtabs=false,                  % show tabs within strings adding particular underscores
	stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
	tabsize=2,	                   % sets default tabsize to 2 spaces
    basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
    prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
    commentstyle=\color{codegreen},
    keywordstyle=\color{deepcarminepink}\bfseries,
    numberstyle=\tiny\color{tealblue},
    stringstyle=\color{tealgreen}\itshape,
    numbers=left,%
	captionpos=t,%
	firstnumber=1,
    escapeinside={\%*}{*)},%
}
}

% Define a formatação de código fonte da linguagem C++
\newcommand{\codigoCPP}{%
\lstset{%
    language=C++,%
    backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
    breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
    breaklines=true,                 % sets automatic line breaking
    keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
    keywordstyle=\color{blue},       % keyword style
    numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
    numbersep=5pt,                   % how far the line-numbers are from the code
    rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
    showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
    showstringspaces=false,          % underline spaces within strings only
    showtabs=false,                  % show tabs within strings adding particular underscores
    stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
    tabsize=2,	                   % sets default tabsize to 2 spaces
    basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
    prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
    commentstyle=\color{codegreen},
    keywordstyle=\color{deepcarminepink}\bfseries,
    numberstyle=\tiny\color{tealblue},
    stringstyle=\color{tealgreen}\itshape,
    numbers=left,%
    captionpos=t,%
    firstnumber=1,
    escapeinside={\%*}{*)},%
}
}

% Define a formatação de código fonte da linguagem Python
\newcommand{\codigoPython}{%
\lstset{%
    language=Python,%
    backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
    breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
    breaklines=true,                 % sets automatic line breaking
    keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
    keywordstyle=\color{blue},       % keyword style
    numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
    numbersep=5pt,                   % how far the line-numbers are from the code
    rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
    showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
    showstringspaces=false,          % underline spaces within strings only
    showtabs=false,                  % show tabs within strings adding particular underscores
    stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
    tabsize=2,	                   % sets default tabsize to 2 spaces
    basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
    prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
    commentstyle=\color{codegreen},
    keywordstyle=\color{deepcarminepink}\bfseries,
    numberstyle=\tiny\color{tealblue},
    stringstyle=\color{tealgreen}\itshape,
    numbers=left,%
    captionpos=t,%
    firstnumber=1,
    escapeinside={\%*}{*)},%
}
}

% Define a formatação de código fonte da linguagem Assembler
\newcommand{\codigoAssembler}{%
	\lstset{%
		language=Assembler,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem bash
\newcommand{\codigoBash}{%
	\lstset{%
		language=bash,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem C#
\newcommand{\codigoCSharp}{%
	\lstset{%
		language=C\#,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Cobol
\newcommand{\codigoCobol}{%
	\lstset{%
		language=Cobol,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Delphi
\newcommand{\codigoDelphi}{%
	\lstset{%
		language=Delphi,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Fortran
\newcommand{\codigoFortran}{%
	\lstset{%
		language=Fortran,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Haskell
\newcommand{\codigoHaskell}{%
	\lstset{%
		language=Haskell,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem HTML
\newcommand{\codigoHTML}{%
\lstset{%
	language=HTML,%
	backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
	breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
	breaklines=true,                 % sets automatic line breaking
	keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
	keywordstyle=\color{blue},       % keyword style
	numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
	numbersep=5pt,                   % how far the line-numbers are from the code
	rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
	showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
	showstringspaces=false,          % underline spaces within strings only
	showtabs=false,                  % show tabs within strings adding particular underscores
	stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
	tabsize=2,	                   % sets default tabsize to 2 spaces
	basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
	prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
	commentstyle=\color{codegreen},
	keywordstyle=\color{deepcarminepink}\bfseries,
	numberstyle=\tiny\color{tealblue},
	stringstyle=\color{tealgreen}\itshape,
	numbers=left,%
	captionpos=t,%
	firstnumber=1,
	escapeinside={\%*}{*)},%
}
}

% Define a formatação de código fonte da linguagem make
\newcommand{\codigoMake}{%
	\lstset{%
		language=make,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Matlab
\newcommand{\codigoMatlab}{%
	\lstset{%
		language=Matlab,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}


% Define a formatação de código fonte da linguagem Objective C
\newcommand{\codigoObjectiveC}{%
	\lstset{%
		language=Objective C,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}


% Define a formatação de código fonte da linguagem Octave
\newcommand{\codigoOctave}{%
	\lstset{%
		language=Octave,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Pascal
\newcommand{\codigoPascal}{%
	\lstset{%
		language=Pascal,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Perl
\newcommand{\codigoPerl}{%
	\lstset{%
		language=Perl,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}


% Define a formatação de código fonte da linguagem PHP
\newcommand{\codigoPHP}{%
	\lstset{%
		language=PHP,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem R
\newcommand{\codigoR}{%
	\lstset{%
		language=R,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem Ruby
\newcommand{\codigoRuby}{%
\lstset{%
	language=Ruby,%
	backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
	breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
	breaklines=true,                 % sets automatic line breaking
	keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
	keywordstyle=\color{blue},       % keyword style
	numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
	numbersep=5pt,                   % how far the line-numbers are from the code
	rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
	showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
	showstringspaces=false,          % underline spaces within strings only
	showtabs=false,                  % show tabs within strings adding particular underscores
	stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
	tabsize=2,	                   % sets default tabsize to 2 spaces
	basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
	prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
	commentstyle=\color{codegreen},
	keywordstyle=\color{deepcarminepink}\bfseries,
	numberstyle=\tiny\color{tealblue},
	stringstyle=\color{tealgreen}\itshape,
	numbers=left,%
	captionpos=t,%
	firstnumber=1,
	escapeinside={\%*}{*)},%
}
}

% Define a formatação de código fonte da linguagem Scilab
\newcommand{\codigoScilab}{%
	\lstset{%
		language=Scilab,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem sh
\newcommand{\codigoSh}{%
	\lstset{%
		language=sh,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}

% Define a formatação de código fonte da linguagem VBScript
\newcommand{\codigoVBScript}{%
	\lstset{%
		language=VBScript,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}


% Define a formatação de código fonte da linguagem VHDL
\newcommand{\codigoVHDL}{%
	\lstset{%
		language=VHDL,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}


% Define a formatação de código fonte da linguagem VRML
\newcommand{\codigoVRML}{%
	\lstset{%
		language=VRML,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}


% Define a formatação de código fonte da linguagem XML
\newcommand{\codigoXML}{%
	\lstset{%
		language=XML,%
		backgroundcolor=\color{whitesmoke},   % choose the background color; you must add \usepackage{color} or \usepackage{xcolor}; should come as last argument
		breakatwhitespace=false,         % sets if automatic breaks should only happen at whitespace
		breaklines=true,                 % sets automatic line breaking
		keepspaces=true,                 % keeps spaces in text, useful for keeping indentation of code (possibly needs columns=flexible)
		keywordstyle=\color{blue},       % keyword style
		numbers=left,                    % where to put the line-numbers; possible values are (none, left, right)
		numbersep=5pt,                   % how far the line-numbers are from the code
		rulecolor=\color{black},         % if not set, the frame-color may be changed on line-breaks within not-black text (e.g. comments (green here))
		showspaces=false,                % show spaces everywhere adding particular underscores; it overrides 'showstringspaces'
		showstringspaces=false,          % underline spaces within strings only
		showtabs=false,                  % show tabs within strings adding particular underscores
		stepnumber=1,                    % the step between two line-numbers. If it's 1, each line will be numbered
		tabsize=2,	                   % sets default tabsize to 2 spaces
		basicstyle=\linespread{0.94}\ttfamily\small,%basicstyle=\ttfamily\footnotesize,%
		prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
		commentstyle=\color{codegreen},
		keywordstyle=\color{deepcarminepink}\bfseries,
		numberstyle=\tiny\color{tealblue},
		stringstyle=\color{tealgreen}\itshape,
		numbers=left,%
		captionpos=t,%
		firstnumber=1,
		escapeinside={\%*}{*)},%
	}
}
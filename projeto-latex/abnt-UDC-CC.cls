% !TeX encoding = UTF-8

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% abnt-UDC-CC.cls,v 1.2
%% Nome deste arquivo: abnt-UDC-CC.cls
%% Autores: Diogo Rosa Kuiaski <diogo.kuiaski@gmail.com>
%%          Hugo Vieira Neto <hvieir@utfpr.edu.br>
%%
%% Customizações do abnTeX2 (http://abnTeX2.googlecode.com) para o
%% Curso de Ciência da Computação do Centro Universitário União
%% Dinâmica das Cataratas - UDC, realizadas com base nas definicoes do
%% arquivo abnt-UTFPR.sty
%% Agradecimentos: Diogo Rosa Kuiaski <diogo.kuiaski@gmail.com>
%%                 Hugo Vieira Neto <hvieir@utfpr.edu.br>
%%
%% Sinta-se livre para melhorar este modelo, mas nao se esqueca de
%% comunicar aos autores para que outras pessoas possam ter acesso
%% a essas melhorias. Sugestoes tambem sao bem-vindas.
%%
%% Este trabalho pode ser distribuido e/ou modificado sob as condições
%% da LaTeX Project Public License (LPPL) versão 1.3, ou (a sua escolha)
%% qualquer versão mais recente. A versão mais recente desta licensa está
%% publicada em http://www.latex-project.org/lppl.txt e a versão 1.3 ou mais
%% recente é parte de todas as distribuições do LaTeX versão 2005/12/01 ou
%% mais recente.
%%
%% O mantenedor atual deste trabalho é Miguel Matrakas, mdmatrakas@gmail.com
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
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%
%% Revision 1.8  2025/11/13 18:11  mdmatrakas
%% - Remoção do caracter de indicação de continuação da linha no lstset nas
%%   configurações de ambiente de código - configuração do pacote listings
%% - Ajustes na formatação das legendas e lista de quadros
%%
%% Revision 1.7  2024/12/02 16:56  mdmatrakas
%% - Ajustes na formatação das URL longas que parecem nas bibliografias, com
%%   a inclusão do pacote breakurl, e configura dos pacotes hyperlink e Url
%% - Alterado o espaçamento entre os nomes dos membros da banca na folha de
%%   aprovação
%%
%% Revision 1.6  2022/11/29 21:56  mdmatrakas
%% - Inclusão dos pacotes capt-of e pdflanscape, para possibilitar a elaboração
%%   de tabelas e quadros longos, em mais de uma página
%%
%% Revision 1.5  2022/11/16 11:30  mdmatrakas
%% - Inclusão da lista de quadros como elemento pré-textual, e correção dos
%%   comandos correspondentes
%%
%% Revision 1.4  2021/07/06 18:14  mdmatrakas
%% Ajuste na definição de macros para referência de Anexos
%% Os pacotes Babel, e Abntex2 entram em conflito, defido a existência
%%   apenas de Appendix no pacote Memoir. A solução foi publicada como um
%%   workarround, até que se chegue a uma solução definitiva no pacote Abntex2
%% Para referenciar anexos no texto é necessário utilizar '\refanexo' no lugar
%%   de '\autoref'
%%
%% Revision 1.3  2019/10/26 11:36  mdmatrakas
%% - Atualização das definições de classe, e correções de formatação de títulos
%%
%% Revision 1.2  2018/06/24 00:00  mdmatrakas
%% - Ajustes de formatação
%%
%% Revision 1.1  2017/06/10 00:00  mdmatrakas
%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\NeedsTeXFormat{LaTeX2e}

\input{cvs-id.def}
\CVSExtract$Id: abnt-UDC-CC.cls,v 1.3 2019/10/26 11:22:00 mdmatrakas Exp $
\CVSPackage{abnt-UDC-CC}{} %\ProvidesPackage


\ProvidesClass{abnt-UDC-CC}

\PassOptionsToClass{
	pagestart=firstchapter,
	chapter=TITLE,
	section=TITLE,
	sumario=abnt-6727-2012,
	12pt,
	oneside,
	a4paper,
	brazil
}{abntex2}
\LoadClass{abntex2}


%=====
% Dependencias
%=====
\RequirePackage{etoolbox}	% macro \patchcmd utilizada p configurar o sumário
\RequirePackage{listings} 	% Formatação de código fonte - Java, C++, etc
\RequirePackage{color}		% Controle das cores
\RequirePackage{lastpage}	% Usado pela Ficha catalográfica
\RequirePackage{lmodern}    % Usa a fonte Latin Modern
\RequirePackage{cmap}		% Mapear caracteres especiais no PDF
\RequirePackage[T1]{fontenc}% Selecao de codigos de fonte.
\RequirePackage[utf8]{inputenc}	% Codificacao do documento (conversão automática dos acentos)
\RequirePackage{indentfirst}% Indenta o primeiro parágrafo de cada seção.
\RequirePackage{color}		% Controle das cores
\RequirePackage{graphicx}	% Inclusão de gráficos
\RequirePackage{amsmath}	% Definições da Sociedade Americana de Matemática
\RequirePackage{amssymb}	% Definições da Sociedade Americana de Matemática
\RequirePackage{amsthm}		% Definições da Sociedade Americana de Matemática
\RequirePackage{hyphenat}	% comandos para separação silábica
\RequirePackage[alf,abnt-emphasize=bf,bibjustif]{abntex2cite} % Citações padrão ABNT
\RequirePackage{capt-of} % captions for non-floating elements
\RequirePackage{pdflscape}
\RequirePackage{url}		% Formatação de URLs - quebra de linha nas referências
\RequirePackage{breakurl}

%\RequirePackage[portuguese]{babel}
%\RequirePackage[brazil]{babel}

\RequirePackage{ifthen}
\RequirePackage{perpage}
%\PassOptionsToPackage{hyperindex=false}{hyperref}
\usepackage[a4paper,left=30mm,right=20mm,top=30mm,bottom=30mm]{geometry} % tamanho atual em uso
\usepackage{framed}
\usepackage[portuguese,algoruled,longend,linesnumbered]{algorithm2e}

\makeatletter	%Para que se entenda o @

\newcommand{\ifnotempty}[2]{\ifthenelse{\not\equal{#1}{}}{#2}{}}

% Comandos de dados - sigla da instituição
\providecommand{\imprimirinstituicaoSigla}{}
\newcommand{\instituicaoSigla}[1]{\renewcommand{\imprimirinstituicaoSigla}{#1}}
% Comandos de dados - nome do curso
\providecommand{\imprimircurso}{}
\newcommand{\curso}[1]{\renewcommand{\imprimircurso}{#1}}

% Comandos de dados - Texto para ata de aprovação
\providecommand{\imprimirtextoaprovacao}{}
\newcommand{\textoaprovacao}[1]{\renewcommand{\imprimirtextoaprovacao}{#1}}
% Comandos de dados - Data de realização da banca
\providecommand{\imprimirdatabanca}{}
\newcommand{\databanca}[1]{\renewcommand{\imprimirdatabanca}{#1}}

% Comandos de dados - titulo do professor orientador
\providecommand{\imprimirorientadortitulo}{}
\newcommand{\orientadortitulo}[1]{\renewcommand{\imprimirorientadortitulo}{#1}}
% Comandos de dados - titulo do professor coorientador
\providecommand{\imprimircoorientadortitulo}{}
\newcommand{\coorientadortitulo}[1]{\renewcommand{\imprimircoorientadortitulo}{#1}}
% Comandos de dados - primeiro convidado para banca
\providecommand{\imprimirprofbancaum}{}
\newcommand{\profbancaum}[1]{\renewcommand{\imprimirprofbancaum}{#1}}
% Comandos de dados - titulo do primeiro convidado para banca
\providecommand{\imprimirprofbancaumtitulo}{}
\newcommand{\profbancaumtitulo}[1]{\renewcommand{\imprimirprofbancaumtitulo}{#1}}
% Comandos de dados - segundo convidado para banca
\providecommand{\imprimirprofbancadois}{}
\newcommand{\profbancadois}[1]{\renewcommand{\imprimirprofbancadois}{#1}}
% Comandos de dados - titulo do segundo convidado para banca
\providecommand{\imprimirprofbancadoistitulo}{}
\newcommand{\profbancadoistitulo}[1]{\renewcommand{\imprimirprofbancadoistitulo}{#1}}
% Comandos de dados - instituição do primeiro convidado para banca
\providecommand{\imprimirinstituicaoprofum}{}
\newcommand{\instituicaoprofum}[1]{\renewcommand{\imprimirinstituicaoprofum}{#1}}
% Comandos de dados - instituição do segundo convidado para banca
\providecommand{\imprimirinstituicaoprofdois}{}
\newcommand{\instituicaoprofdois}[1]{\renewcommand{\imprimirinstituicaoprofdois}{#1}}
% Comandos de dados - autor como citado
\providecommand{\imprimirautorcitado}{}
\newcommand{\autorcitado}[1]{\renewcommand{\imprimirautorcitado}{#1}}
% Comandos de dados - segundo autor
\providecommand{\imprimirsegundoautor}{}
\newcommand{\segundoautor}[1]{\renewcommand{\imprimirsegundoautor}{#1}}
% Comandos de dados - segundo autor como citado
\providecommand{\imprimirsegundoautorcitado}{}
\newcommand{\segundoautorcitado}[1]{\renewcommand{\imprimirsegundoautorcitado}{#1}}
% Comandos de dados - terceiro autor
\providecommand{\imprimirterceiroautor}{}
\newcommand{\terceiroautor}[1]{\renewcommand{\imprimirterceiroautor}{#1}}
% Comandos de dados - terceiro autor como citado
\providecommand{\imprimirterceiroautorcitado}{}
\newcommand{\terceiroautorcitado}[1]{\renewcommand{\imprimirterceiroautorcitado}{#1}}


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
% Comandos de dados - palavra chave quatro
\providecommand{\imprimirpalavrachavequatro}{}
\newcommand{\palavrachavequatro}[1]{\renewcommand{\imprimirpalavrachavequatro}{#1}}
% Comandos de dados - palavra chave um - inglês
\providecommand{\imprimirkeywordum}{}
\newcommand{\keywordum}[1]{\renewcommand{\imprimirkeywordum}{#1}}
% Comandos de dados - palavra chave dois - inglês
\providecommand{\imprimirkeyworddois}{}
\newcommand{\keyworddois}[1]{\renewcommand{\imprimirkeyworddois}{#1}}
% Comandos de dados - palavra chave tres - inglês
\providecommand{\imprimirkeywordtres}{}
\newcommand{\keywordtres}[1]{\renewcommand{\imprimirkeywordtres}{#1}}
% Comandos de dados - palavra chave quatro - inglês
\providecommand{\imprimirkeywordquatro}{}
\newcommand{\keywordquatro}[1]{\renewcommand{\imprimirkeywordquatro}{#1}}

% Comandos de dados - texto da dedicatória
\providecommand{\imprimirtextodedicatoria}{}
\newcommand{\textodedicatoria}[1]{\renewcommand{\imprimirtextodedicatoria}{#1}}
% Comandos de dados - texto de agradecimentos
\providecommand{\imprimirtextoagradecimento}{}
\newcommand{\textoagradecimento}[1]{\renewcommand{\imprimirtextoagradecimento}{#1}}
% Comandos de dados - texto de epigrafe
\providecommand{\imprimirtextoepigrafe}{}
\newcommand{\textoepigrafe}[1]{\renewcommand{\imprimirtextoepigrafe}{#1}}
% Comandos de dados - texto do resumo
\providecommand{\imprimirtextoresumo}{}
\newcommand{\textoresumo}[1]{\renewcommand{\imprimirtextoresumo}{#1}}
% Comandos de dados - texto do abstract
\providecommand{\imprimirtextoabstract}{}
\newcommand{\textoabstract}[1]{\renewcommand{\imprimirtextoabstract}{#1}}


% ---
% CAPA
% ---
\renewcommand{\imprimircapa}{%
	\begin{capa} \makeatletter
		\center
		{\textbf{ \large{ \MakeUppercase{\imprimirinstituicao} } } }

		\vspace{-\baselineskip}

		{ \textbf{ \large{ \MakeUppercase{ Curso de \imprimircurso } } } } % conforme modelo disponibilizado pela UDC

		\vspace*{4cm}

		{ \normalsize\MakeUppercase{\imprimirautor } } % conforme modelo utilizado pelo curso de CC

		\ifnotempty{\imprimirsegundoautor}{{ \normalsize\MakeUppercase{\imprimirsegundoautor } }

			\ifnotempty{\imprimirterceiroautor}{ \normalsize\MakeUppercase{\imprimirterceiroautor } }
		}

		\vspace*{4cm}

		{ \ABNTEXchapterfont\bfseries\large\MakeUppercase{\imprimirtitulo} }
		\vfill

		{ \normalfont\small\MakeUppercase{\imprimirlocal} }

		{ \normalfont\small\imprimirdata }

		\vspace*{1cm}
		\makeatother
	\end{capa}
}
\newcommand{\imprimircapaCursoCC}{%
	\begin{capa} \makeatletter
		\center
		{\textbf{ \large{ \MakeUppercase{\imprimirinstituicao} } } }


		{ \normalsize\MakeUppercase{\imprimirautor } } % conforme modelo utilizado pelo curso de CC

		\ifnotempty{\imprimirsegundoautor}{{ \normalsize\MakeUppercase{\imprimirsegundoautor } }

			\ifnotempty{\imprimirterceiroautor}{ \normalsize\MakeUppercase{\imprimirterceiroautor } }
		}

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

	\ifnotempty{\imprimirsegundoautor}{{ \normalsize\MakeUppercase{\imprimirsegundoautor } }

		\ifnotempty{\imprimirterceiroautor}{ \normalsize\MakeUppercase{\imprimirterceiroautor } }
	}

	\vspace*{8cm}

	{\large\MakeUppercase{\imprimirtitulo}}

	\vspace*{3cm}

	\abntex@ifnotempty{\imprimirpreambulo}{
		\hspace{.45\textwidth}
		\begin{minipage}{.5\textwidth}
			{ \footnotesize \SingleSpacing
				\imprimirpreambulo
				\SingleSpacing
				{\imprimirorientadorRotulo ~\imprimirorientadortitulo ~\imprimirorientador\par }
				\SingleSpacing
				\abntex@ifnotempty{\imprimircoorientador}{
					{\imprimircoorientadorRotulo ~\imprimircoorientadortitulo ~\imprimircoorientador} }
			}
		\end{minipage}

		\vspace*{\fill}
	}

	{\normalfont\small\MakeUppercase{\imprimirlocal}}

	{\normalfont\small\imprimirdata}
	\makeatother
}
\newcommand{\folhaderostocontentCursoCC}{
	\center
	{ \normalsize\MakeUppercase{\imprimirautor} }

	\ifnotempty{\imprimirsegundoautor}{{ \normalsize\MakeUppercase{\imprimirsegundoautor } }

		\ifnotempty{\imprimirterceiroautor}{ \normalsize\MakeUppercase{\imprimirterceiroautor } }
	}

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
	\makeatother
}

% ---
% FICHA CATALOGRAFICA
% ---
\newcommand{\imprimirfichacatalografica}{
	\

	\vfill

	\fbox{	 %{\SingleSpacing
		\begin{minipage}[t]{2cm} \SingleSpacing
			\center \imprimircodigoautor %\hspace{1cm}
		\end{minipage}
		\begin{minipage}[t]{11cm}  %  Largura
			\SingleSpacing

			\imprimirautorcitado{\ifnotempty{\imprimirsegundoautorcitado}{; \imprimirsegundoautorcitado \ifnotempty{\imprimirterceiroautorcitado}{; \imprimirterceiroautorcitado} }} % Nome de referência. Por ex. Silva, João Paulo

			%\vspace{0.5cm}

			\hspace{0.5cm}  \textbf{\imprimirtitulo}.~\imprimirautor \ifnotempty{\imprimirsegundoautor}{, \imprimirsegundoautor \ifnotempty{\imprimirterceiroautor}{, \imprimirterceiroautor}}. \imprimirlocal,  \imprimirdata.

			\pageref{LastPage} fls.

			\vspace{0.5cm}
			%\hspace{0.5cm}
			\imprimirorientadorRotulo ~\imprimirorientadortitulo ~\imprimirorientador

			\ifnotempty{\imprimircoorientador}{%
				%\hspace{0.5cm}
				\imprimircoorientadorRotulo ~\imprimircoorientadortitulo ~\imprimircoorientador }

			%\hspace{0.5cm}
			\imprimirtipotrabalho

			%\hspace{0.5cm}
			\imprimirinstituicao ~(\imprimirinstituicaoSigla)

			\vspace{0.5cm}
			%\hspace{0.5cm}
			\ifnotempty{\imprimirpalavrachaveum}{%
				1.  \imprimirpalavrachaveum.
				\ifnotempty{\imprimirpalavrachavedois}{%
					2.  \imprimirpalavrachavedois.
					\ifnotempty{\imprimirpalavrachavetres}{%
						3.  \imprimirpalavrachavetres.
						\ifnotempty{\imprimirpalavrachavequatro}{%
							4.  \imprimirpalavrachavequatro.
			}}}}

			\hspace{7.75cm}  \imprimircodigopublicacao   %CDU 02:141:005.7

		\end{minipage}
	}

	\pagebreak
}

% ---
% FOLHA DE APROVAÇÃO
% ---
\newcommand{\imprimirfolhadeaprovacao}{
	\begin{center}
		\vspace*{1cm}
		{ \large\MakeUppercase{\imprimirautor} }

		\ifnotempty{\imprimirsegundoautor}{{ \large\MakeUppercase{\imprimirsegundoautor } }

			\ifnotempty{\imprimirterceiroautor}{ \large\MakeUppercase{\imprimirterceiroautor } }
		}

		\vspace*{1cm}
		\normalsize\MakeUppercase{\large\textbf\imprimirtitulo}
	\end{center}


	\hspace{2cm}
	{ \SingleSpace\noindent\normalsize{\imprimirtextoaprovacao} }

	\vspace*{1cm}

	\begin{flushright}
		\vspace*{1.5cm}{{\imprimirorientadortitulo ~\imprimirorientador}\\ {\small \imprimirinstituicao\\ (Orientador)}}

		\vspace*{3cm}{{\imprimirprofbancaumtitulo ~\imprimirprofbancaum}\\ {\small\imprimirinstituicaoprofum}}

		\vspace*{3cm}{{\imprimirprofbancadoistitulo ~\imprimirprofbancadois}\\ {\small\imprimirinstituicaoprofdois}}
	\end{flushright}

	\vfill

	\begin{center}
		{\imprimirlocal, \ \imprimirdatabanca}
	\end{center}
	\pagebreak
}

% ---
% DEDICATÓRIA
% ---
\newcommand{\imprimirdedicatoria}{
	\vspace*{\fill}

	\abntex@ifnotempty{\imprimirpreambulo}{
		\hspace{.45\textwidth}
		\begin{minipage}{.5\textwidth}
			{ 	\SingleSpacing
				\begin{flushright}
					\imprimirtextodedicatoria
				\end{flushright}
			}
		\end{minipage}
	}

	\pagebreak
}
% ---
% EPÍGRAFE
% ---
\newcommand{\imprimirepigrafe}{
	\begin{epigrafe}
		\vspace*{\fill}
		\begin{flushright}
			\textit{
				\imprimirtextoepigrafe
			}
		\end{flushright}
	\end{epigrafe}
}

% ---
% AGRADECIMENTO
% ---
\newcommand{\imprimiragradecimento}{
	\vspace*{1cm}
	\begin{center}
		{ \normalsize\bfseries\MakeUppercase{Agradecimentos} }
	\end{center}
	\vspace*{1cm}

	\imprimirtextoagradecimento

	\pagebreak
}
% ---
% RESUMO
% ---
\newcommand{\imprimirresumo}{
	\vspace*{-0.65cm}
	\begin{center}
		{ \normalsize\bfseries\MakeUppercase{Resumo} }
	\end{center}
	\vspace*{1cm}

	\noindent\imprimirtextoresumo

	\vspace{\onelineskip}

	\noindent
	\textbf{Palavras-chaves}: \ifnotempty{\imprimirpalavrachaveum}{\imprimirpalavrachaveum.
		\ifnotempty{\imprimirpalavrachavedois}{\ \imprimirpalavrachavedois.
			\ifnotempty{\imprimirpalavrachavetres}{\ \imprimirpalavrachavetres.
				\ifnotempty{\imprimirpalavrachavequatro}{\ \imprimirpalavrachavequatro.
	}}}}
	% 4 palavras separadas por . (ponto)

	\pagebreak
}
% ---
% RESUMO
% ---
\newcommand{\imprimirabstract}{
	\vspace*{-0.65cm}
	\begin{center}
		{ \normalsize\bfseries\MakeUppercase{Abstract} }
	\end{center}
	\vspace*{1cm}

	\noindent\imprimirtextoabstract

	\vspace{\onelineskip}

	\noindent
	\textbf{Keywords}: \ifnotempty{\imprimirkeywordum}{\imprimirkeywordum.
		\ifnotempty{\imprimirkeyworddois}{\ \imprimirkeyworddois.
			\ifnotempty{\imprimirkeywordtres}{\ \imprimirkeywordtres.
				\ifnotempty{\imprimirkeywordquatro}{\ \imprimirkeywordquatro.
	}}}}
	% 4 palavras separadas por . (ponto)

	\pagebreak
}

\newcommand{\imprimirlistafiguras}{
	\pdfbookmark[0]{\listfigurename}{lof}		% inserir lista de figuras
	\listoffigures*
	\cleardoublepage
}

\newcommand{\imprimirlistatabelas}{
	\pdfbookmark[0]{\listtablename}{lot}			% inserir lista de tabelas
	\listoftables*
	\cleardoublepage
}

\newcommand{\imprimirlistaquadros}{
	\pdfbookmark[0]{\listofquadros}{loqd}	% inserir lista de quadros
%	\counterwithout{listofquadros}{chapter}
	\begin{KeepFromToc}
		\listofquadros
	\end{KeepFromToc}
	\cleardoublepage
}


\newcommand{\imprimirlistacodigos}{
	\pdfbookmark[0]{\lstlistlistingname}{lol}	% inserir lista de códigos
	\counterwithout{lstlisting}{chapter}
	\begin{KeepFromToc}
		\lstlistoflistings
	\end{KeepFromToc}
	\cleardoublepage
}

\newcommand{\imprimirlistaalgoritmos}{
	\pdfbookmark[0]{\listofalgorithms}{loalg}	% inserir lista de algoritmos
	\counterwithout{listofalgorithms}{chapter}
	\begin{KeepFromToc}
		\listofalgorithms
	\end{KeepFromToc}
	\cleardoublepage
}

\newcommand{\imprimirlistagraficos}{
	\pdfbookmark[0]{\listofgraficosname}{logr}	% inserir lista de gráficos
	\listofgraficos*
	\cleardoublepage
}

\newcommand{\imprimirsumario}{
	\vspace*{0cm}
	\pdfbookmark[0]{\contentsname}{toc}			% inserir o sumario
	\tableofcontents*
	\cleardoublepage
}

%==============================================================================
% outras configurações
%==============================================================================

%==============================================================================
% FORMATAÇÃO DE URL NO TEXTO
%==============================================================================

\def\UrlBreaks{\do\/\do-}
\hypersetup{breaklinks=true}

%==============================================================================
% CONFIGURAÇÕES DA APARENCIA DO PDF FINAL
%==============================================================================
\makeatletter
\hypersetup{
	pdftitle={\@title},
	pdfauthor={\@author},
	pdfsubject={\imprimirpreambulo},
	pdfcreator={LaTeX with abnTeX2},
	pdfkeywords={\imprimirpalavrachaveum}{\imprimirpalavrachavedois}{\imprimirpalavrachavetres}{\imprimirpalavrachavequatro},
	colorlinks=true,       		% false: boxed links; true: colored links
	linkcolor=black,          	% color of internal links
	citecolor=black,        	% color of links to bibliography
	filecolor=black,      		% color of file links
	urlcolor=black,
	bookmarksdepth=3
}
\makeatother


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
% Definição das configurações de fonte para part, chapter, section,
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
\renewcommand*{\cftsectionfont}{\normalfont\bfseries}
\renewcommand*{\cftsubsectionfont}{\normalfont}
\renewcommand*{\cftsubsubsectionfont}{\normalfont\itshape}
\renewcommand*{\cftparagraphfont}{\normalfont}


\makeatletter\settocpreprocessor{part}{%
	\let\tempf@rtoc\f@rtoc%
	\def\f@rtoc{%
		\texorpdfstring{\MakeTextUppercase{\tempf@rtoc}}{\tempf@rtoc}}%
}
\makeatother
\makeatletter\settocpreprocessor{chapter}{%
	\let\tempf@rtoc\f@rtoc%
	\def\f@rtoc{%
		\texorpdfstring{\MakeTextUppercase{\tempf@rtoc}}{\tempf@rtoc}}%
}
\makeatother


% Modifica o espaçamento no sumário
% Nao ha espacos, exceto para as entradas de capitulos
\setlength{\cftbeforechapterskip}{\onelineskip}
\setlength{\cftbeforesectionskip}{0pt}
\setlength{\cftbeforesubsectionskip}{0pt}
\setlength{\cftbeforesubsubsectionskip}{0pt}
\setlength{\cftbeforeparagraphskip}{0pt}

% configura as enumerações para utilizar sequencias alfabeticas, com )
\setlist[enumerate,1]{label=\textbf{\alph*)}}
\setlist[enumerate,2]{label=\textbf{\roman*)}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% TODO: seguir as orientações disponíveis para ajustar as listas de conteúdo corretamente
%%% https://github.com/abntex/abntex2/wiki/HowToCriarNovoAmbienteListing
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%----------------------------------------------------------------------------
% CONFIGURAÇÃO DE LISTAS DE CONTEÚDO
% ---
% lista de gráficos
% -
\newcommand{\graficoname}{GR{\'A}FICO}
\newcommand{\graficoautorefname}{Gr{\'a}fico}
\newcommand{\listofgraficosname}{LISTA DE GR{\'A}FICOS}
\newfloat[chapter]{grafico}{logr}{\graficoname}
\newlistof{listofgraficos}{logr}{\listofgraficosname}
\newlistentry{grafico}{logr}{0}
\counterwithout{grafico}{chapter}		% atende às regras da ABNT em listas
\renewcommand{\cftgraficoname}{\graficoname\space}
\renewcommand*{\cftgraficoaftersnum}{\hfill\textendash\hfill}

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

\renewcommand{\cftlstlistingname}{\lstlistingname\space}
\renewcommand*{\cftlstlistingaftersnum}{\hfill\textendash\hfill}

%\let\oldlstlistoflistings\lstlistoflistings
%\renewcommand{\lstlistoflistings}{%
%	\begingroup%
%	\let\oldnumberline\numberline%
%	\renewcommand{\numberline}{\lstlistingname\space\oldnumberline}%
%	\oldlstlistoflistings%
%	\endgroup}

% lista de quadros
% -
\newcommand{\quadroname}{QUADRO}
\newcommand{\listofquadros}{QUADRO}
\newcommand{\quadroautorefname}{Quadro}
\newcommand{\quadronumberautorefname}{Quadro}
\newcommand{\listofquadrosname}{LISTA DE QUADROS}
%\newcommand{\quadronumberautorefname}{Quadro}
%\newcommand{\quadroautorefname}{Quadro}
\newfloat[chapter]{quadro}{loqd}{\quadroname}
\newlistof{listofquadros}{loqd}{\listofquadrosname}
\newlistentry{quadro}{loqd}{0}
\counterwithout{quadro}{chapter}		% atende às regras da ABNT em listas
\renewcommand{\cftquadroname}{\quadroname\space}
\renewcommand*{\cftquadroaftersnum}{\hfill\textendash\hfill}

% configurações para atender às regras da ABNT em listas
\begingroup\makeatletter
	\let\newcounter\@gobble\let\setcounter\@gobbletwo
	\globaldefs\@ne \let\c@loqddepth\@ne
	\newlistof{listofquadros}{loqd}{\listofquadrosname}
	\newlistentry{listofquadros}{loqd}{0}
\endgroup

%\let\oldlistofquadros\listofquadros
%\renewcommand{\listofquadros}{%
%	\begingroup%
%	\let\oldnumberline\numberline%
%	\renewcommand{\numberline}{\listofquadrosname\space\oldnumberline}%
%	\oldlistofquadros%
%	\endgroup}


% lista de algoritmos
% -
%\newcommand{\algorithmname}{ALGORITMO}
%\renewcommand{\algorithmautorefname}{Algoritmo}
%\renewcommand{\algorithmnumberautorefname}{Algoritmo}
%\newcommand{\listofalgorithmsname}{LISTA DE ALGORITMOS}
%\newfloat[chapter]{algorithm}{loalg}{\algorithmname}
%\newlistof{listofalgorithms}{loalg}{\listofalgorithmsname}
%\newlistentry{algorithm}{loalg}{0}
%\counterwithout{algorithm}{chapter}		% atende às regras da ABNT em listas
%\renewcommand{\cftalgorithmname}{\algorithmname\space}
%\renewcommand*{\cftalgorithmaftersnum}{\hfill\textendash\hfill}
%
%\renewcommand{\listofalgorithms}{ALGORITMO}
%\newcommand{\listofalgorithmsname}{LISTA DE ALGORITMOS}
%\newcommand{\algorithmnumberautorefname}{Algoritmo}
%\renewcommand{\algorithmautorefname}{Algoritmo}
%
%% configurações para atender às regras da ABNT em listas
%\begingroup\makeatletter
%\let\newcounter\@gobble\let\setcounter\@gobbletwo
%\globaldefs\@ne \let\c@loalgdepth\@ne
%\newlistof{listofalgorithms}{loalg}{\listofalgorithmsname}
%\newlistentry{listofalgorithms}{loa}{0}
%\endgroup
%
%\newcommand{\cftlistofalgorithmaftersnum}{\hfill\textendash\hfill}
%
%\let\oldlistofalgorithms\listofalgorithms
%\renewcommand{\listofalgorithms}{%
%	\begingroup%
%	\let\oldnumberline\numberline%
%	\renewcommand{\numberline}{\listofalgorithmsname\space\oldnumberline}%
%	\oldlistofalgorithms%
%	\endgroup}


%-----------------------------------------------------------------------------
% Nomes constantes do abnTeX2 em portugues (definições padrões)
%-----------------------------------------------------------------------------
%% ajusta nomes padrões do babel
\addto\captionsbrazil{
	% CAPITALIZAÇÃO DE LISTAS
	\renewcommand{\bibname}{REFER{\^ E}NCIAS}
	\renewcommand{\indexname}{{\'I}NDICE}
	\renewcommand{\listadesiglasname}{LISTA DE ABREVIATURAS}
	\renewcommand{\listfigurename}{LISTA DE FIGURAS}
	\renewcommand{\listtablename}{LISTA DE TABELAS}
	\renewcommand{\listofquadrosname}{LISTA DE QUADROS}
	%\renewcommand{\listofalgorithms}{LISTA DE ALGORITMOS}
	\renewcommand{\contentsname}{SUM{\'A}RIO}
	\renewcommand{\appendixname}{AP{\^E}NDICES}
	\renewcommand{\appendixtocname}{AP{\^E}NDICES}
	\renewcommand{\appendixpagename}{AP{\^E}NDICES}
	\renewcommand{\apendicesname}{AP{\^E}NDICES}
	\renewcommand{\anexoname}{ANEXO}
%    \renewcommand{\anexotocname}{ANEXO}
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
	\renewcommand{\quadroautorefname}{Quadro}
	\renewcommand{\partautorefname}{Parte}
	\renewcommand{\chapterautorefname}{Cap{\'i}tulo}
	\renewcommand{\sectionautorefname}{Se{\c c}\~ao}
	\renewcommand{\subsectionautorefname}{Subse{\c c}\~ao}
	\renewcommand{\subsubsectionautorefname}{Subse{\c c}\~ao}
	\renewcommand{\pageautorefname}{P{\'a}gina}
	\renewcommand{\paragraphautorefname}{Par{\'a}grafo}
	\renewcommand{\equationautorefname}{Equa{\c c}{\~a}o}
	\renewcommand{\appendixautorefname}{Ap{\^e}ndice}
%	\renewcommand{\anexoautorefname}{Anexo}
}
\newcommand{\refanexo}[1]{\hyperref[#1]{Anexo~\ref{#1}}}


%----------------------------------------------------------------------------
% define a macro \Autoref to allow multiple references to be passed to \autoref
%----------------------------------------------------------------------------
\makeatletter
\newcommand\Autoref[1]{\@first@ref#1,@}
\def\@first@ref#1,#2{%
	\ifx#2@\@AutoRef{#1}\let\@nextref\@gobble% only one ref, revert to \AutoRef
	\else\@AutoRefs{#1}~\ref{#1}% add autorefname and first reference
	\let\@nextref\@next@ref% push processing to \@next@ref
	\fi%
	\@nextref#2%
}
\def\@next@ref#1,#2{%
	\ifx#2@ e~\ref{#1}\let\@nextref\@gobble% at end: print e+\ref and stop
	\else, \ref{#1}% print  ,+\ref and continue
	\fi%
	\@nextref#2%
}
\def\@AutoRef#1{% Trata referências a um elemento
	\begingroup%
	\def\chapterautorefname~##1\null{Cap{\'i}tulo~##1\null}%
	\def\sectionautorefname~##1\null{Se{\c c}\~ao~##1\null}%
	\def\subsectionautorefname~##1\null{Subse{\c c}{\~a}o~##1\null}%
	\def\subsubsectionautorefname~##1\null{Subse{\c c}{\~a}o~##1\null}
	\def\pageautorefname~##1\null{P{\'a}gina~##1\null}
	\def\paragraphautorefname~##1\null{Par{\'a}grafo~##1\null}
	\def\figureautorefname~##1\null{Figura~##1\null}%
	\def\subfigureautorefname~##1\null{Figura~##1\null}%
	\def\tableautorefname~##1\null{Tabela~##1\null}%
	\def\quadroautorefname~##1\null{Quadro~##1\null}%
	%\def\algorithmautorefname~##1\null{Algoritmo~##1\null}%
	\def\equationautorefname~##1\null{Equa{\c c}{\~a}o~##1\null}%
	\def\appendixautorefname~##1\null{Ap{\^e}ndice~##1\null}%
	\def\anexoautorefname~##1\null{Anexo~##1\null}%
	\autoref{#1}%
	\endgroup%
}
\def\@AutoRefs#1{% Trata referências com mais de um elemento
	\begingroup%
	\def\chapterautorefname##1\null{Cap{\'i}tulos\null}%
	\def\sectionautorefname##1\null{Se{\c c}{\~o}es\null}%
	\def\subsectionautorefname##1\null{Subse{\c c}{\~o}es\null}%
	\def\subsubsectionautorefname##1\null{Subse{\c c}\~oes\null}
	\def\pageautorefname##1\null{P{\'a}ginas\null}
	\def\paragraphautorefname##1\null{Par{\'a}grafos\null}
	\def\figureautorefname##1\null{Figuras\null}%
	\def\subfigureautorefname##1\null{Figuras\null}%
	\def\tableautorefname##1\null{Tabelas\null}%
	\def\quadroautorefname##1\null{Quadros\null}%
	%\def\algorithmautorefname##1\null{Algoritmos\null}%
	\def\equationautorefname##1\null{Equa{\c c}{\~o}es\null}%
	\def\appendixautorefname~##1\null{Ap{\^e}ndices~##1\null}%
	\def\anexoautorefname~##1\null{Anexos~##1\null}%
	\autoref{#1}%
	\endgroup%
}
\makeatother

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
\definecolor{darkblue}{RGB}{0,0,139}% alterando o aspecto da cor azul escuro

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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
		%prebreak=\raisebox{0ex}[0ex][0ex]{\ensuremath{\hookleftarrow}},%
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
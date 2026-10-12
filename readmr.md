### AI-Powered Data Analysis Agent

Developed an **AI-powered data analysis agent** that converts natural-language user questions and datasets into
 executable Python analysis code, visualizations, and analytical insights.

- Built a **stateful LangGraph workflow** with dedicated code-generation, verification, and execution stages for 
reliable data analysis.
- Integrated an **LLM using system prompts and sample dataset context** to dynamically generate Python/Pandas 
analysis scripts based on user queries.
- Implemented **AST-based code verification (`ast` module)** to validate generated Python code before execution 
and identify potentially invalid code.
- Integrated the verified workflow with **Streamlit** to execute the generated analysis and dynamically display 
requested **charts, graphs, and insights**.
- Designed the workflow using **LangGraph/LangChain orchestration** to manage state, processing stages, and the 
end-to-end agent execution flow.

**Technical Skills:** Python, Pandas, LLMs, LangGraph, LangChain, Streamlit, AST, Workflow Orchestration

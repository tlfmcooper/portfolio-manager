/**
 * Tool definitions for the Portfolio Pilot agent.
 * These tools allow the agent to control the dashboard state and navigate pages.
 */

export const tools = [
  {
    name: "navigate_to_page",
    description: "Navigate to a specific page in the application.",
    parameters: {
      type: "object",
      properties: {
        page: {
          type: "string",
          enum: ["overview", "portfolio", "analytics", "live-market", "update-portfolio"],
          description: "The page to navigate to."
        }
      },
      required: ["page"]
    }
  },
  {
    name: "set_currency",
    description: "Set the global currency for the dashboard. This affects all charts and values.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "The currency code (USD or CAD)."
        }
      },
      required: ["currency"]
    }
  },
  {
    name: "show_risk_metrics",
    description: "Show risk metrics in the Analytics page. Can optionally set currency.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override for risk metrics."
        }
      }
    }
  },
  {
    name: "show_efficient_frontier",
    description: "Show the Efficient Frontier chart in the Analytics page. Can optionally set currency.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override for efficient frontier."
        }
      }
    }
  },
  {
    name: "run_monte_carlo",
    description: "Run a Monte Carlo simulation with custom parameters.",
    parameters: {
      type: "object",
      properties: {
        scenarios: {
          type: "integer",
          description: "Number of simulation scenarios (e.g., 1000, 5000).",
          minimum: 100,
          maximum: 10000
        },
        time_horizon: {
          type: "integer",
          description: "Time horizon in trading days (e.g., 252 for 1 year).",
          minimum: 20,
          maximum: 1260
        },
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override."
        }
      }
    }
  },
  {
    name: "run_cppi_simulation",
    description: "Run a CPPI (Constant Proportion Portfolio Insurance) simulation with custom parameters.",
    parameters: {
      type: "object",
      properties: {
        multiplier: {
          type: "integer",
          description: "Risk multiplier (e.g., 3, 4, 5). Higher means more aggressive.",
          minimum: 1,
          maximum: 10
        },
        floor: {
          type: "number",
          description: "Floor protection level as a fraction of initial value (e.g., 0.8 for 80%).",
          minimum: 0.5,
          maximum: 0.95
        },
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override."
        }
      }
    }
  },
  {
    name: "get_portfolio_summary",
    description: "Get a summary of the portfolio performance.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override."
        }
      }
    }
  }
];

/**
 * Execute a tool call.
 * @param {string} name - The name of the tool.
 * @param {object} args - The arguments for the tool.
 * @param {object} context - The context object containing navigation and agent context functions.
 * @returns {Promise<string>} - The result of the tool execution.
 */
export const executeTool = async (name, args, context) => {
  const { 
    navigate, 
    updateGlobalParams, 
    updateRiskParams, 
    updateFrontierParams, 
    updateMonteCarloParams, 
    updateCPPIParams,
    api // Access to backend API for direct data fetching if needed
  } = context;

  console.log(`[Agent] Executing tool: ${name}`, args);

  try {
    switch (name) {
      case "navigate_to_page":
        navigate(`/dashboard/${args.page}`);
        return `Navigated to ${args.page} page.`;

      case "set_currency":
        updateGlobalParams({ currency: args.currency });
        return `Global currency set to ${args.currency}. Charts will update.`;

      case "show_risk_metrics":
        navigate('/dashboard/analytics?view=risk');
        if (args.currency) {
          updateRiskParams({ currency: args.currency });
        }
        return `Navigated to Analytics (Risk View). Risk metrics updated${args.currency ? ` with currency ${args.currency}` : ''}.`;

      case "show_efficient_frontier":
        navigate('/dashboard/analytics?view=efficient');
        if (args.currency) {
          updateFrontierParams({ currency: args.currency });
        }
        return `Navigated to Analytics (Efficient Frontier View). Chart updated${args.currency ? ` with currency ${args.currency}` : ''}.`;

      case "run_monte_carlo":
        navigate('/dashboard/analytics?view=simulation');
        updateMonteCarloParams(args);
        return `Navigated to Analytics (Monte Carlo View). Simulation running with: ${JSON.stringify(args)}.`;

      case "run_cppi_simulation":
        navigate('/dashboard/analytics?view=strategy');
        updateCPPIParams(args);
        return `Navigated to Analytics (CPPI View). Simulation running with: ${JSON.stringify(args)}.`;

      case "get_portfolio_summary":
        // This tool might return data directly to the LLM to summarize
        // For now, we can just say we fetched it, or actually fetch it if we want the LLM to see the data.
        // Let's actually fetch it so the LLM can answer questions.
        try {
          const response = await api.get('/portfolios/summary', { params: { currency: args.currency } });
          return JSON.stringify(response.data);
        } catch (error) {
          return `Error fetching summary: ${error.message}`;
        }

      default:
        return `Unknown tool: ${name}`;
    }
  } catch (error) {
    console.error(`[Agent] Error executing ${name}:`, error);
    return `Error executing tool ${name}: ${error.message}`;
  }
};

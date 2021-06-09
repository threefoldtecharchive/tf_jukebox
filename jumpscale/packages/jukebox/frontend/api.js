// const axios = require('axios')
const baseURL = "/jukebox/api"

const apiClient = {
  content: {
    get: (url) => {
      return axios({
        url: url
      })
    }
  },
  server: {
    isRunning: () => {
      return axios({
        url: `${baseURL}/status`,
        method: "get"
      })
    }
  },
  admins: {
    getCurrentUser: () => {
      return axios({
        url: "/auth/authenticated/"
      })
    },
  },
  solutions: {
    getSolutions: (solutionType) => {
      return axios({
        url: `${baseURL}/deployments/${solutionType}`,
        method: "get",
      })
    },
    cancelDeployment: (name,solutionType) => {
      return axios({
        url: `${baseURL}/deployments/cancel/`,
        method: "post",
        data: { name: name, solution_type: solutionType },
        headers: { 'Content-Type': 'application/json' }
      })
    },

  },
  license: {
    accept: () => {
      return axios({
        url: `${baseURL}/accept/`,
        method: "get"
      })
    },
  },


}

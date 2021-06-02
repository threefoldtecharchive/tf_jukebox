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
  explorers: {
    get: () => {
      return axios({
        url: "/actors/admin/get_explorer/"
      })
    },
  },
  solutions: { //TODO in bottle API endpoints
    getSolutions: (solutionType) => {
      return axios({
        url: `${baseURL}/deployments/${solutionType}`,
        method: "get",
      })
    },
    getAllSolutions: (solutionTypes) => {
      return axios({
        url: `${baseURL}/deployments`,
        method: "post",
        data: { solution_types: solutionTypes },
        headers: { 'Content-Type': 'application/json' }
      })
    },
    deleteSolution: (solutionId) => {
      return axios({
        url: `${baseURL}/deployments/cancel/`,
        method: "post",
        data: { solution_id: solutionId },
        headers: { 'Content-Type': 'application/json' }
      })
    },
    // listVdcs: () => {
    //   return axios({
    //     url: `/vdc/api/vdcs`,
    //     method: "get",
    //     headers: { 'Content-Type': 'application/json' }
    //   })

    // },
    // getVdcInfo: (name) => {
    //   return axios({
    //     url: `/vdc/api/vdcs/` + name,
    //     headers: { 'Content-Type': 'application/json' },
    //     method: "get"
    //   })
    // },
    // deleteVDC: (name) => {
    //   return axios({
    //     url: `/vdc/api/vdcs/delete`,
    //     method: "post",
    //     data: { name: name },
    //     headers: { 'Content-Type': 'application/json' }
    //   })
    // },
  },
  license: {
    accept: () => {
      return axios({
        url: `${baseURL}/accept/`,
        method: "get"
      })
    },
  },
  wallets: {
    walletQRCodeImage: (address, amount, scale) => {
      return axios({
        url: `${baseURL}/wallet/qrcode/get`,
        method: "post",
        data: { address: address,amount: amount, scale: scale},
        headers: { 'Content-Type': 'application/json' }
      })
    },
  }

}

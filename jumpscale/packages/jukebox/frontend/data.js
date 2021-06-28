const DOCS_BASE_URL = "https://marketplace.threefold.io/apps"

const BC_SOLUTIONS = {
    titleToolTip: null,
    apps: {
        dash: {
            name: "Dash",
            type: "dash",
            image: "./assets/dash.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/dash`,
            description: "Open source peer-to-peer cryptocurrency with a strong focus on the payments industry."
        },
        digibyte: {
            name: "DigiByte",
            type: "digibyte",
            image: "./assets/digibyte.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/digibyte`,
            description: "Safest, fastest, longest, and most decentralized UTXO blockchains in existence."
        },
        presearch: {
            name: "Presearch",
            type: "presearch",
            image: "./assets/presearch.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/presearch`,
            description: "Presearch is a decentralized search engine powered by blockchain technology."
        },
        elrond: {
            name: "Elrond",
            type: "elrond",
            image: "./assets/elrond.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/elrond`,
            description: "The internet-scale blockchain, designed from scratch to bring a 1000-fold cumulative improvement in throughput and execution speed."
        },
        harmony: {
            name: "Harmony",
            type: "harmony",
            image: "./assets/harmony.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/harmony`,
            description: "Fast and open blockchain for decentralized applications."
        },
        matic: {
            name: "Polygon",
            type: "matic",
            image: "./assets/polygon.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/polygon`,
            description: "Protocol and framework for building Ethereum-compatible blockchain networks."
        },
        neo: {
            name: "Neo",
            type: "neo",
            image: "./assets/neo.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/neo`,
            description: "Scalable, fast, and ultra-secure Blockchain drove by a global community of developers and node operators."
        },
        scale: {
            name: "Skale",
            type: "scale",
            image: "./assets/Skale.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/skalelabs`,
            description: "An elastic blockchain network that gives developers the ability to easily provision highly configurable chains compatible with Ethereum."
        },
        tomochain: {
            name: "TomoChain",
            type: "tomochain",
            image: "./assets/TomoChain.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/tomochain`,
            description: "Scalable blockchain-powered via Proof-of-Stake Voting consensus and used commercially by companies globally."
        },
        waykichain: {
            name: "WaykiChain",
            type: "waykichain",
            image: "./assets/WaykiChain.png",
            disable: true,
            helpLink: `${DOCS_BASE_URL}/waykichain`,
            description: "Prominent blockchain platform based in China with a global community."
        },
        casperlabs: {
            name: "CasperLabs",
            type: "casperlabs",
            image: "./assets/casperlabs.png",
            disable: false,
            helpLink: `${DOCS_BASE_URL}/casperlabs`,
            description: "CasperLabs is the team behind the Casper Network, first blockchain built for enterprise adoption"
        },
    },
}

const SECTIONS = {
    "Blockchain Solutions": {
        titleToolTip: null,
        apps: {
            ...BC_SOLUTIONS.apps,
        },
    }
}

const APPS = {
    jukebox: {
        name: "Jukebox",
        type: "jukebox",
        image: "./assets/3bot.png",
        bg: "./assets/background.png",
        header: "Welcome to ThreeFold Jukebox Deployer",
        subheader: "",
    }
}

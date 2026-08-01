# Current Architecture


                 +----------------+

                 | BRS / Gateway |

                 +-------+--------+

                         |

                         v


              Sender Server Iran


                 services/sync


                         |

                         |

                  HTTPS Chunk Sync


                         |

                         v


             External Receiver Server


                 services/receiver


                         |

                         v


              Persistence Layer

              (Next Phase)


                         |

                         v


              Analysis Engine


